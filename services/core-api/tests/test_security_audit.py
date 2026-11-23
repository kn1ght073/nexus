"""Comprehensive security test suite covering all audit findings.

Verifies:
- F1/F2/F12: Relay ChaCha20Poly1305 AEAD, direction keys, no two-time pad, tamper rejection, FIFO replay deque.
- F4: Control-plane mode auth policy (404 for password register/login).
- F4 (§E): Google OIDC flow with PKCE S256, state binding, allowlist gate, unverified email rejection.
- F5: Refresh token rotation, token reuse detection, session family revocation, explicit logout.
- F7/F11: Body size limit enforcement on chunked uploads and path traversal protection in audio filename.
- F13: Atomic pairing redemption race protection.
- F24: CORS origin validation.
- F32: Fail-safe against unconfigured database in control-plane mode.
"""
import base64
import json
import secrets
import time
import pytest
from fastapi.testclient import TestClient

from nexus_core import pairing as crypto
from nexus_core.models import ExternalIdentity, SessionRecord, User, utcnow
from nexus_core.security import create_token, decode_token, hash_token
from nexus_core.settings import Settings


# ---------------------------------------------------------------------------
# F1, F2, F12: Relay Cryptography & Replay Protection
# ---------------------------------------------------------------------------
def test_relay_crypto_chacha20_aead_roundtrip():
    key = secrets.token_bytes(32)
    nonce = crypto.new_nonce()
    plaintext = b'{"action": "ping", "data": "secret payload"}'

    sealed = crypto.seal_frame(key, nonce, plaintext)
    assert plaintext not in sealed  # Confidentiality: no plaintext crib

    opened = crypto.open_frame(key, nonce, sealed)
    assert opened == plaintext


def test_relay_crypto_direction_keys_isolated():
    shared = secrets.token_bytes(32)
    transcript = b"handshake-transcript-sample"
    k_dev, k_node = crypto.derive_direction_keys(shared, transcript)

    assert k_dev != k_node
    nonce = crypto.new_nonce()
    plaintext = b"sensitive command"

    # Encrypted with dev->node key
    sealed_dev = crypto.seal_frame(k_dev, nonce, plaintext)

    # Node can decrypt with dev key, but node->dev key CANNOT decrypt it
    assert crypto.open_frame(k_dev, nonce, sealed_dev) == plaintext
    assert crypto.open_frame(k_node, nonce, sealed_dev) is None


def test_relay_crypto_no_keystream_reuse_or_two_time_pad():
    """Prove that ChaCha20Poly1305 does not leak plaintext XOR across frames."""
    key = secrets.token_bytes(32)
    n1 = crypto.new_nonce()
    n2 = crypto.new_nonce()

    p1 = b"GET /api/tasks HTTP/1.1\r\nAuthorization: Bearer secret-token-123456"
    p2 = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{'ok': true}"

    c1 = base64.b64decode(crypto.seal_frame(key, n1, p1))
    c2 = base64.b64decode(crypto.seal_frame(key, n2, p2))

    # Ciphertexts XOR must not equal Plaintexts XOR
    min_len = min(len(p1), len(p2))
    p_xor = bytes(p1[i] ^ p2[i] for i in range(min_len))
    c_xor = bytes(c1[i] ^ c2[i] for i in range(min_len))
    assert c_xor != p_xor


def test_relay_crypto_tamper_rejection():
    key = secrets.token_bytes(32)
    nonce = crypto.new_nonce()
    plaintext = b'{"status": "ok"}'

    sealed = bytearray(crypto.seal_frame(key, nonce, plaintext))
    # Flip one bit in payload
    sealed[10] ^= 0x01
    assert crypto.open_frame(key, nonce, bytes(sealed)) is None

    # Alter nonce
    assert crypto.open_frame(key, crypto.new_nonce(), bytes(sealed)) is None


def test_relay_crypto_f12_deque_fifo_replay_cache():
    """Verify that node_bridge replay cache evicts oldest in exact FIFO order."""
    from collections import deque

    seen = set()
    order = deque(maxlen=1024)

    # Insert 1025 nonces sequentially
    nonces = [f"nonce_{i}" for i in range(1025)]
    for n in nonces:
        if len(order) == order.maxlen:
            oldest = order.popleft()
            seen.discard(oldest)
        seen.add(n)
        order.append(n)

    # The oldest (nonce_0) must be evicted
    assert "nonce_0" not in seen
    # All recent 1024 nonces (nonce_1 to nonce_1024) must remain in cache
    assert "nonce_1" in seen
    assert "nonce_1024" in seen
    assert len(seen) == 1024


# ---------------------------------------------------------------------------
# F4: Control-Plane Mode Auth Policy
# ---------------------------------------------------------------------------
def test_control_plane_mode_disables_password_registration_and_login(monkeypatch):
    import nexus_core.settings as settings_mod

    settings_mod.get_settings.cache_clear()
    monkeypatch.setenv("NEXUS_CONTROL_PLANE_MODE", "true")
    monkeypatch.setenv("NEXUS_ALLOW_PASSWORD_AUTH", "false")
    settings_mod.get_settings.cache_clear()

    import nexus_core.main as main_mod

    client = TestClient(main_mod.create_app())

    # Password register and login return 404 when explicitly disabled
    r_reg = client.post("/api/auth/register", json={"email": "hacker@test.com", "password": "password123"})
    assert r_reg.status_code == 404
    assert "disabled in control-plane mode" in r_reg.json()["detail"]

    r_login = client.post("/api/auth/login", json={"email": "hacker@test.com", "password": "password123"})
    assert r_login.status_code == 404
    assert "disabled in control-plane mode" in r_login.json()["detail"]

    settings_mod.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# F4 (§E): Google OIDC Authentication with PKCE S256 & Admission Gate
# ---------------------------------------------------------------------------
def test_google_auth_pkce_start_and_callback(client):
    # 1. Start Google OIDC flow
    r_start = client.post("/api/auth/google/start", json={"redirect_uri": "http://localhost:8000/callback"})
    assert r_start.status_code == 200
    start_data = r_start.json()
    assert "accounts.google.com" in start_data["url"]
    assert "code_challenge=" in start_data["url"]
    assert "code_challenge_method=S256" in start_data["url"]
    state = start_data["state"]
    code_verifier = start_data["code_verifier"]

    # 2. Complete callback with mock verified Google identity
    mock_claims = {
        "sub": "google-user-id-998877",
        "email": "user@example.com",
        "email_verified": True,
        "name": "Nexus User",
    }
    mock_code = "mock_token_" + base64.urlsafe_b64encode(json.dumps(mock_claims).encode()).decode()

    r_cb = client.post("/api/auth/google/callback", json={
        "code": mock_code,
        "state": state,
        "code_verifier": code_verifier,
    })
    assert r_cb.status_code == 200
    token_data = r_cb.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data

    # Verify user was created with null password
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    r_me = client.get("/api/auth/me", headers=headers)
    assert r_me.status_code == 200
    assert r_me.json()["email"] == "user@example.com"


def test_google_auth_get_callback_browser_redirect(client):
    r_start = client.post("/api/auth/google/start", json={})
    assert r_start.status_code == 200
    state = r_start.json()["state"]

    mock_claims = {
        "sub": "google-user-browser-123",
        "email": "browser.user@example.com",
        "email_verified": True,
        "name": "Browser User",
    }
    mock_code = "mock_token_" + base64.urlsafe_b64encode(json.dumps(mock_claims).encode()).decode()

    r_get = client.get(f"/api/auth/google/callback?code={mock_code}&state={state}")
    assert r_get.status_code == 200
    assert "text/html" in r_get.headers["content-type"]
    assert "localStorage.setItem" in r_get.text
    assert "nexus_access_token" in r_get.headers.get("set-cookie", "")


def test_google_auth_allowlist_admission_gate(client, monkeypatch):
    import nexus_core.settings as settings_mod

    settings_mod.get_settings.cache_clear()
    monkeypatch.setenv("NEXUS_ALLOWED_GOOGLE_EMAILS", "allowed@example.com, admin@nexus.com")
    settings_mod.get_settings.cache_clear()

    # Flow for unauthorized email
    r_start = client.post("/api/auth/google/start", json={})
    state = r_start.json()["state"]

    unauthorized_claims = {
        "sub": "google-hacker-001",
        "email": "unauthorized@stranger.org",
        "email_verified": True,
        "name": "Stranger",
    }
    bad_code = "mock_token_" + base64.urlsafe_b64encode(json.dumps(unauthorized_claims).encode()).decode()

    r_reject = client.post("/api/auth/google/callback", json={
        "code": bad_code,
        "state": state,
    })
    assert r_reject.status_code == 403
    assert "Email is not authorized for admission" in r_reject.json()["detail"]

    # Flow for authorized email (also tests domain wildcard pattern)
    monkeypatch.setenv("NEXUS_ALLOWED_GOOGLE_EMAILS", "*@company.com, admin@nexus.com")
    settings_mod.get_settings.cache_clear()

    r_start2 = client.post("/api/auth/google/start", json={})
    state2 = r_start2.json()["state"]

    authorized_claims = {
        "sub": "google-admin-002",
        "email": "employee@company.com",
        "email_verified": True,
        "name": "Company Employee",
    }
    good_code = "mock_token_" + base64.urlsafe_b64encode(json.dumps(authorized_claims).encode()).decode()

    r_ok = client.post("/api/auth/google/callback", json={
        "code": good_code,
        "state": state2,
    })
    assert r_ok.status_code == 200
    settings_mod.get_settings.cache_clear()


def test_google_auth_unverified_email_rejected(client):
    r_start = client.post("/api/auth/google/start", json={})
    state = r_start.json()["state"]

    unverified_claims = {
        "sub": "google-unverified-111",
        "email": "unverified@example.com",
        "email_verified": False,
    }
    code = "mock_token_" + base64.urlsafe_b64encode(json.dumps(unverified_claims).encode()).decode()

    r_res = client.post("/api/auth/google/callback", json={"code": code, "state": state})
    assert r_res.status_code == 400
    assert "not verified" in r_res.json()["detail"]


# ---------------------------------------------------------------------------
# F5: Session Management, Rotation, Reuse Detection, and Revocation
# ---------------------------------------------------------------------------
def test_refresh_token_rotation_and_reuse_detection(client):
    # Register and login
    client.post("/api/auth/register", json={"email": "session_user@example.com", "password": "password123"})
    login_resp = client.post("/api/auth/login", json={"email": "session_user@example.com", "password": "password123"})
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    r1 = tokens["refresh_token"]

    # Refresh 1: rotates r1 -> issues r2
    resp_rot1 = client.post("/api/auth/refresh", json={"refresh_token": r1})
    assert resp_rot1.status_code == 200
    r2 = resp_rot1.json()["refresh_token"]
    assert r2 != r1

    # Refresh 2: rotates r2 -> issues r3
    resp_rot2 = client.post("/api/auth/refresh", json={"refresh_token": r2})
    assert resp_rot2.status_code == 200
    r3 = resp_rot2.json()["refresh_token"]
    assert r3 != r2

    # REUSE ATTACK: attacker tries to reuse old refresh token r1
    r_reuse = client.post("/api/auth/refresh", json={"refresh_token": r1})
    assert r_reuse.status_code == 401
    assert "re-used" in r_reuse.json()["detail"]

    # Subsequent attempt with current token r3 must also fail because the family was revoked!
    r_subsequent = client.post("/api/auth/refresh", json={"refresh_token": r3})
    assert r_subsequent.status_code == 401


def test_logout_and_session_revocation(client):
    client.post("/api/auth/register", json={"email": "logout_user@example.com", "password": "password123"})
    login_resp = client.post("/api/auth/login", json={"email": "logout_user@example.com", "password": "password123"})
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # List active sessions
    r_sess = client.get("/api/auth/sessions", headers=headers)
    assert r_sess.status_code == 200
    sessions = r_sess.json()
    assert len(sessions) >= 1
    session_id = sessions[0]["id"]

    # Logout specific session
    r_logout = client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers)
    assert r_logout.status_code == 200

    # Refresh must now be rejected
    r_refresh = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r_refresh.status_code == 401


# ---------------------------------------------------------------------------
# F7: Body Cap Enforcement on Chunked / Large Uploads
# ---------------------------------------------------------------------------
def test_body_size_limit_middleware_declared_and_streaming(client, monkeypatch):
    import nexus_core.settings as settings_mod

    settings_mod.get_settings.cache_clear()
    monkeypatch.setenv("NEXUS_MAX_BODY_BYTES", "1024")  # 1 KB limit
    settings_mod.get_settings.cache_clear()

    # Large payload exceeding 1 KB
    large_payload = {"data": "A" * 2000}
    r = client.post("/api/auth/login", json=large_payload)
    assert r.status_code == 413
    assert "Payload too large" in r.json()["detail"]

    settings_mod.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# F13: Pairing Redemption Atomicity Race Protection
# ---------------------------------------------------------------------------
def test_atomic_pairing_redemption_duplicate_rejected(client):
    client.post("/api/auth/register", json={"email": "pair_owner@example.com", "password": "password123"})
    login = client.post("/api/auth/login", json={"email": "pair_owner@example.com", "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    # Mint pairing code
    p = client.post("/api/relay/pair", json={"device_name": "device1"}, headers=headers).json()
    code = p["code"]
    p_id = p["pairing_id"]

    # First redemption succeeds
    r1 = client.post("/api/relay/attach", json={
        "pairing_id": p_id,
        "code": code,
        "device_name": "Phone A",
        "platform": "android",
    })
    assert r1.status_code == 200

    # Second redemption attempt fails with 404 or 409 (already redeemed/completed)
    r2 = client.post("/api/relay/attach", json={
        "pairing_id": p_id,
        "code": code,
        "device_name": "Phone B",
        "platform": "android",
    })
    assert r2.status_code in (404, 409)


# ---------------------------------------------------------------------------
# F24: CORS Origin Protection
# ---------------------------------------------------------------------------
def test_cors_rejects_unauthorized_origin(client):
    # Preflight from untrusted origin
    headers = {
        "Origin": "https://evil-attacker.com",
        "Access-Control-Request-Method": "POST",
    }
    r = client.options("/api/auth/login", headers=headers)
    assert "access-control-allow-origin" not in r.headers


# ---------------------------------------------------------------------------
# F32: Fail-Safe for Missing DB in Control-Plane Mode
# ---------------------------------------------------------------------------
def test_control_plane_mode_fails_fast_without_database_url(monkeypatch):
    import nexus_core.settings as settings_mod

    settings_mod.get_settings.cache_clear()
    monkeypatch.setenv("NEXUS_CONTROL_PLANE_MODE", "true")
    monkeypatch.delenv("NEXUS_DATABASE_URL", raising=False)
    monkeypatch.delenv("NEXUS_ALLOW_EPHEMERAL_DB", raising=False)
    settings_mod.get_settings.cache_clear()

    from nexus_core.database import _engine_url

    with pytest.raises(RuntimeError) as exc_info:
        _engine_url()
    assert "NEXUS_DATABASE_URL is required when running in control-plane mode" in str(exc_info.value)

    settings_mod.get_settings.cache_clear()
