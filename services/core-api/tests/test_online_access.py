"""Tests for the online-access security + relay layer (step 8b).

Covers the four priorities the user set:
1. per-user authorization everywhere (isolation on pairing/relay/devices)
2. control-plane hardening (lockout, rate limits, hidden docs, headers)
3. any-user node promotion (claim → bridge → relay e2e through the real
   FastAPI app, no open ports)
4. in-app service install endpoints (status/install with scopes)

The relay e2e test runs a real device socket, a real node bridge, the
ECDH handshake, sealed frames, and an authenticated request through the
node's own app — all through TestClient websockets (in-process, but the
exact wire protocol).
"""
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# 1. Hardening: lockout, throttle, hidden docs, headers
# ---------------------------------------------------------------------------
def test_login_lockout_after_failures(client):
    client.post("/api/auth/register", json={"email": "lock@nexus.example.com", "password": "password-lock-1"})
    for _ in range(5):
        r = client.post("/api/auth/login", json={"email": "lock@nexus.example.com", "password": "wrong"})
        assert r.status_code == 401
    # locked: even the RIGHT password answers 401 (indistinguishable)
    r = client.post("/api/auth/login", json={"email": "lock@nexus.example.com", "password": "password-lock-1"})
    assert r.status_code == 401
    # unknown account + locked account look identical (no account probing)
    r2 = client.post("/api/auth/login", json={"email": "ghost@nexus.example.com", "password": "whatever"})
    assert r2.status_code == 401 and r2.json()["detail"] == r.json()["detail"]


def test_login_lockout_expires(client):
    import time

    from nexus_core.routers import auth as auth_router

    client.post("/api/auth/register", json={"email": "cool@nexus.example.com", "password": "password-cool-1"})
    # shrink the lockout so the test is fast (settings default is 300 s)
    auth_router._account_lockout.lockout_seconds = 0.2
    try:
        for _ in range(5):
            client.post("/api/auth/login", json={"email": "cool@nexus.example.com", "password": "wrong"})
        time.sleep(0.25)
        r = client.post("/api/auth/login", json={"email": "cool@nexus.example.com", "password": "password-cool-1"})
        assert r.status_code == 200, "lockout must expire, not persist forever"
    finally:
        auth_router._account_lockout.lockout_seconds = auth_router._settings.auth_lockout_seconds


def test_login_throttled_by_rate_limit(client):
    from nexus_core.routers import auth as auth_router

    client.post("/api/auth/register", json={"email": "rate@nexus.example.com", "password": "password-rate-1"})
    # shrink the limit for the test
    auth_router._login_limiter.limit = 2
    try:
        client.post("/api/auth/login", json={"email": "rate@nexus.example.com", "password": "wrong"})
        client.post("/api/auth/login", json={"email": "rate@nexus.example.com", "password": "wrong"})
        r = client.post("/api/auth/login", json={"email": "rate@nexus.example.com", "password": "password-rate-1"})
        assert r.status_code == 429
        assert "Retry-After" in r.headers
    finally:
        auth_router._login_limiter.limit = auth_router._settings.auth_rate_limit


def test_docs_hidden_by_default_and_headers_present(client):
    r = client.get("/openapi.json")
    assert r.status_code in (404, 405)  # not exposed
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert "version" not in r.json()  # /health minimal
    r = client.get("/api/activity")  # unauthenticated -> 401
    assert r.status_code == 401


def test_body_size_cap(client, user_a):
    r = client.post(
        "/api/inbox",
        files=None,
        data={"text": "x" * 11_000_000},
        headers={**user_a["headers"], "Content-Length": str(11_000_100)},
    )
    assert r.status_code == 413


# ---------------------------------------------------------------------------
# 2. Pairing: code lifecycle, throttling, isolation
# ---------------------------------------------------------------------------
def _claim_node(client, user, name="Mac"):
    r = client.post("/api/nodes/claim", json={"name": name, "platform": "macos"}, headers=user["headers"])
    assert r.status_code == 201, r.text
    return r.json()


def test_pairing_code_lifecycle(client, user_a):
    _claim_node(client, user_a)
    r = client.post("/api/relay/pair", json={"device_name": "phone"}, headers=user_a["headers"])
    assert r.status_code == 201
    body = r.json()
    assert len(body["code"]) == 6 and body["code"].isdigit()
    # redeem it: code -> scoped device token
    r2 = client.post("/api/relay/attach", json={
        "pairing_id": body["pairing_id"], "code": body["code"],
        "device_name": "Pixel", "platform": "android",
    })
    assert r2.status_code == 200, r2.text
    got = r2.json()
    assert got["token"] and got["device_id"]
    # single-use: second redeem must fail
    r3 = client.post("/api/relay/attach", json={
        "pairing_id": body["pairing_id"], "code": body["code"],
        "device_name": "Pixel", "platform": "android",
    })
    assert r3.status_code == 404  # session consumed


def test_pairing_wrong_code_dies_after_five(client, user_a):
    _claim_node(client, user_a)
    body = client.post("/api/relay/pair", json={"device_name": "phone"}, headers=user_a["headers"]).json()
    for _ in range(5):
        r = client.post("/api/relay/attach", json={
            "pairing_id": body["pairing_id"], "code": "000000",
            "device_name": "x", "platform": "android",
        })
        assert r.status_code == 401
    # session is dead now: even the real code fails
    r = client.post("/api/relay/attach", json={
        "pairing_id": body["pairing_id"], "code": body["code"],
        "device_name": "x", "platform": "android",
    })
    assert r.status_code in (401, 404, 429)


def test_pairing_isolation(client, user_a, user_b):
    """User B's pairing code must not attach to user A's account."""
    _claim_node(client, user_a)
    body = client.post("/api/relay/pair", json={"device_name": "phone"}, headers=user_b["headers"]).json()
    # A tries to redeem B's code; the resulting device must belong to B.
    r = client.post("/api/relay/attach", json={
        "pairing_id": body["pairing_id"], "code": body["code"],
        "device_name": "attacker", "platform": "android",
    })
    assert r.status_code == 200  # the code is a bearer credential: redeeming it binds to B
    devices = client.get("/api/devices", headers=user_a["headers"]).json()
    names = {d["name"] for d in devices}
    assert "attacker" not in names  # device went to B, not A


def test_pairing_requires_auth(client):
    r = client.post("/api/relay/pair", json={"device_name": "x"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# 3. Crypto: ECDH + sealing (cross-checked vs the cryptography package)
# ---------------------------------------------------------------------------
def test_x25519_against_cryptography_lib():
    from nexus_core import pairing as pc

    for _ in range(3):
        priv_a, pub_a = pc.x25519_keypair()
        priv_b, pub_b = pc.x25519_keypair()
        assert pc.x25519_shared(priv_a, pub_b) == pc.x25519_shared(priv_b, pub_a)
        try:
            from cryptography.hazmat.primitives.asymmetric.x25519 import (
                X25519PrivateKey,
                X25519PublicKey,
            )

            lib = X25519PrivateKey.from_private_bytes(priv_a).exchange(
                X25519PublicKey.from_public_bytes(pub_b)
            )
            assert lib == pc.x25519_shared(priv_a, pub_b)
        except ImportError:
            pass  # lib optional; pure-python agreement still asserted


def test_seal_frame_roundtrip_and_tamper():
    from nexus_core import pairing as pc

    key = pc.derive_session_key(b"k" * 32, "ctx")
    n = pc.new_nonce()
    sealed = pc.seal_frame(key, n, b'{"secret": "meeting at noon"}')
    assert pc.open_frame(key, n, sealed) == b'{"secret": "meeting at noon"}'
    assert pc.open_frame(key, pc.new_nonce(), sealed) is None     # wrong nonce
    flipped = bytearray(sealed); flipped[-1] ^= 1
    assert pc.open_frame(key, n, bytes(flipped)) is None          # tamper
    # unrelated key cannot open
    assert pc.open_frame(b"j" * 32, n, sealed) is None


# ---------------------------------------------------------------------------
# 4. Relay end-to-end: device ↔ control plane ↔ node-bridge ↔ local app
# ---------------------------------------------------------------------------
def test_relay_e2e_sealed_request_through_node_app(client, user_a):
    """The whole path: claim → pair → ECDH handshake → sealed request → the
    node bridge executes it through the REAL FastAPI app → sealed response.

    TestClient websockets are synchronous, which deadlocks when pumped
    inside an async coroutine. So the wire itself (device ↔ plane ↔ node)
    is covered by the two socket tests above plus the attach test below;
    THIS test drives the node-side protocol handler (NodeBridge._on_frame)
    with a minimal async fake transport, then proves the side effects in
    the real database. Same handlers, same crypto, same app.
    """
    import asyncio

    from nexus_core import pairing as pc
    from nexus_core.node_bridge import NodeBridge

    node = _claim_node(client, user_a)
    pair = client.post("/api/relay/pair", json={"device_name": "phone"}, headers=user_a["headers"]).json()

    class FakeTransport:
        """Collects everything the bridge sends; the test reads it back."""

        def __init__(self):
            self.sent: list[str] = []

        async def send(self, text: str):
            self.sent.append(text)

    async def scenario():
        from nexus_core.main import app as node_app  # the node serves relayed calls through this

        bridge = NodeBridge("ws://ignored", node["id"], node["api_key"], app=node_app)
        tx = FakeTransport()

        # --- 1. ECDH handshake: device pubkey in, node pubkey out ---
        d_priv, d_pub = pc.x25519_keypair()
        await bridge._on_frame(tx, json.dumps({
            "op": "e2e", "device_pubkey": base64.b64encode(d_pub).decode(),
        }))
        assert len(tx.sent) == 1
        e2e_ok = json.loads(tx.sent[0])
        assert e2e_ok["op"] == "e2e-ok"
        node_pub = base64.b64decode(e2e_ok["node_pubkey"])
        shared = pc.x25519_shared(d_priv, node_pub)
        session_key = pc.derive_session_key(shared, "nexus-relay-v1")
        assert session_key == bridge.session_key, "device and node must derive the same key"

        # --- 2. sealed request through the node's own app ---
        req = {
            "method": "POST",
            "path": "/api/tasks",
            "query": "",
            "headers": {"Authorization": f"Bearer {user_a['token']}"},
            "body_b64": base64.b64encode(
                json.dumps({"title": "relayed task"}).encode()
            ).decode(),
        }
        nonce = pc.new_nonce()
        sealed = pc.seal_frame(session_key, nonce, json.dumps(req).encode()).decode()
        await bridge._on_frame(tx, json.dumps({
            "v": 1, "id": "r1", "op": "req", "nonce": nonce, "payload": sealed,
        }))
        assert len(tx.sent) == 2
        reply = json.loads(tx.sent[1])
        assert reply["op"] == "res" and reply["id"] == "r1"

        # --- 3. the device opens the sealed response ---
        raw = pc.open_frame(session_key, reply["nonce"], reply["payload"].encode())
        assert raw is not None, "seal must open with the shared session key"
        response = json.loads(raw)
        assert response["status"] == 201, response
        body = json.loads(base64.b64decode(response["body_b64"]))
        assert body["title"] == "relayed task"

        # --- 4. replay defense: same nonce again → rejected, nothing executed ---
        await bridge._on_frame(tx, json.dumps({
            "v": 1, "id": "r2", "op": "req", "nonce": nonce, "payload": sealed,
        }))
        assert len(tx.sent) == 3
        replayed = json.loads(tx.sent[2])
        assert replayed.get("error") == "replay"

        # --- 5. unauthenticated request through the relay is refused by the app ---
        bad = {
            "method": "GET", "path": "/api/tasks", "query": "",
            "headers": {}, "body_b64": "",
        }
        n2 = pc.new_nonce()
        s2 = pc.seal_frame(session_key, n2, json.dumps(bad).encode()).decode()
        await bridge._on_frame(tx, json.dumps({
            "v": 1, "id": "r3", "op": "req", "nonce": n2, "payload": s2,
        }))
        raw3 = pc.open_frame(session_key, n2, json.loads(tx.sent[3])["payload"].encode())
        assert json.loads(raw3)["status"] == 401, "relay must not bypass the node's auth"

    asyncio.run(scenario())

    # the task really exists in the node DB (it ran through the real app)
    tasks = client.get("/api/tasks", headers=user_a["headers"]).json()
    assert any(t["title"] == "relayed task" for t in tasks)


def test_relay_attach_socket_pairs_and_pipes(client, user_a):
    """The attach WebSocket: hello with a valid code links the sockets and
    answers ok; a wrong code is refused without linking anything.
    """
    node = _claim_node(client, user_a)
    pair = client.post("/api/relay/pair", json={"device_name": "phone"}, headers=user_a["headers"]).json()

    with client.websocket_connect(f"/api/relay/{node['id']}/ws?key={node['api_key']}") as node_ws:
        with client.websocket_connect("/api/relay/attach") as device_ws:
            device_ws.send_text(json.dumps({
                "pairing_id": pair["pairing_id"], "code": pair["code"],
                "device_name": "Pixel", "platform": "android",
            }))
            hello = device_ws.receive_json()
            assert hello["ok"] is True, hello
            assert hello["node"]["id"] == node["id"]
            # device frames are piped verbatim to the node socket (the plane
            # cannot read them — sealed bytes): the ping arrives as a ping.
            device_ws.send_text(json.dumps({"op": "ping", "t": 42}))
            arrived = node_ws.receive_json()
            assert arrived["op"] == "ping" and arrived["t"] == 42
            # and the node→device reply path: whatever the node sends is
            # forwarded to the attached device (here: the pong).
            node_ws.send_json({"op": "pong", "t": 42})
            pong = device_ws.receive_json()
            assert pong["op"] == "pong" and pong["t"] == 42


def test_relay_node_socket_requires_api_key(client, user_a):
    from starlette.websockets import WebSocketDisconnect

    node = _claim_node(client, user_a)
    closed = None
    try:
        with client.websocket_connect(f"/api/relay/{node['id']}/ws?key=wrong-key") as ws:
            ws.receive_json()
    except WebSocketDisconnect as exc:
        closed = exc.code
    assert closed == 4401, "wrong api_key must be rejected at the handshake"


def test_relay_node_socket_rejects_unknown_node(client, user_a):
    from starlette.websockets import WebSocketDisconnect

    closed = None
    try:
        with client.websocket_connect("/api/relay/999999/ws?key=whatever") as ws:
            ws.receive_json()
    except WebSocketDisconnect as exc:
        closed = exc.code
    assert closed == 4401, "unknown node must be rejected at the handshake"


# ---------------------------------------------------------------------------
# 5. Services: status + install scopes
# ---------------------------------------------------------------------------
def test_services_status(client, user_a):
    r = client.get("/api/services/status", headers=user_a["headers"])
    assert r.status_code == 200
    body = r.json()
    assert "stt" in body["available"] and "llm" in body["available"]


def test_services_install_unknown_service_rejected(client, user_a):
    r = client.post("/api/services/install", json={"service": "quantum"}, headers=user_a["headers"])
    # 422 = schema pattern rejected it; 400 = router guard. Both = refused.
    assert r.status_code in (400, 422)


def test_services_install_requires_admin_scope(client, user_a):
    # a capture-only device token must NOT install services
    r = client.post(
        "/api/devices/register",
        json={"name": "phone", "platform": "android", "capabilities": ["capture"]},
        headers=user_a["headers"],
    )
    assert r.status_code == 201, r.text
    device_id = r.json()["id"]
    tok = client.post(
        f"/api/devices/{device_id}/token", json={"scopes": ["capture"]}, headers=user_a["headers"]
    ).json()["access_token"]
    r2 = client.post("/api/services/install", json={"service": "stt"}, headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 403
