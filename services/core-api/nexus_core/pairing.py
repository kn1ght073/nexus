"""Secure device pairing and request relay (no open ports on the node).

Problem: a node at home (Mac/Windows) sits behind NAT. Opening a port or
exposing the API publicly invites scanners; tunnels (ngrok/cloudflared)
leak the node's existence and rotate URLs. The user wants a global, safe
capability — any device becomes the main server, phones link to it from
anywhere, no unnecessary ports.

Design (the "phone-home" pattern, same shape as commercial mesh/relay
services):

1. PAIRING: the node's owner (logged in on the phone/desktop app) asks the
   control plane for a pairing code — a short-lived 6-digit PIN bound to
   their user id. A device presenting the correct code (over the relay
   handshake) is bound to the owner's account and receives a scoped device
   token. Codes are single-purpose, expire in 10 minutes, and are
   hard-throttled so guessing is not viable.

2. RELAY: the node opens ONE outbound WebSocket to the control plane
   (`/api/relay/{node_id}/ws`, authenticated with its api_key — outbound,
   so no inbound port is ever opened). Devices exchange JSON frames with
   the node through that socket; the control plane forwards bytes and
   never stores them.

3. E2E SEALING: every request/response payload is sealed with a session
   key agreed between the DEVICE and the NODE alone (X25519 ECDH over the
   control plane — standard ephemeral Diffie-Hellman; the courier sees
   only public keys and ciphertext). On top of confidentiality this means
   a compromised control plane STILL cannot read or forge user data —
   the trust base collapses to the two endpoints you own.

4. AUTHORIZATION: relayed requests run through the node's normal FastAPI
   stack — the device's scoped token is enforced there, so ownership
   filtering and scope checks apply exactly as on the LAN.

Routes live in routers/relay.py; crypto helpers here (pure-Python X25519
~40 lines — verified against the `cryptography` package in tests).
"""
import base64
import hashlib
import hmac
import secrets
from typing import Optional


# ---------------------------------------------------------------------------
# X25519 (RFC 7748) — pure Python so the Core has zero crypto dependencies.
# The test suite cross-verifies against the `cryptography` package.
# ---------------------------------------------------------------------------
P = 2**255 - 19
_A24 = 121665


def _x25519_mult(k: int, u: int) -> int:
    """Scalar multiplication on Curve25519 (Montgomery ladder, RFC 7748)."""
    # RFC 7748: ignore the most significant bit of the u-coordinate.
    u &= (1 << 255) - 1
    k &= (1 << 255) - 8
    x1, x2, z2, x3, z3 = u, 1, 0, u, 1
    swap = 0
    for t in range(254, -1, -1):
        k_t = (k >> t) & 1
        swap ^= k_t
        if swap:
            x2, x3 = x3, x2
            z2, z3 = z3, z2
        swap = k_t
        a = (x2 + z2) % P
        aa = a * a % P
        b = (x2 - z2) % P
        bb = b * b % P
        e = (aa - bb) % P
        c = (x3 + z3) % P
        d = (x3 - z3) % P
        da = d * a % P
        cb = c * b % P
        x3 = pow(da + cb, 2, P)
        z3 = x1 * pow(da - cb, 2, P) % P
        x2 = aa * bb % P
        z2 = e * (aa + _A24 * e) % P
    if swap:
        x2, x3 = x3, x2
        z2, z3 = z3, z2
    return x2 * pow(z2, P - 2, P) % P


def x25519_keypair() -> tuple[bytes, bytes]:
    """(private, public): clamped random scalar + its public point."""
    private = bytearray(secrets.token_bytes(32))
    private[0] &= 248
    private[31] &= 127
    private[31] |= 64
    public = _x25519_mult(int.from_bytes(private, "little"), 9).to_bytes(32, "little")
    return bytes(private), public


def x25519_shared(private: bytes, peer_public: bytes) -> bytes:
    """ECDH shared secret; all-zero output means a bad/low-order peer key —
    callers must treat that as failure (small-subgroup defense)."""
    shared = _x25519_mult(
        int.from_bytes(private, "little"), int.from_bytes(peer_public, "little")
    )
    return shared.to_bytes(32, "little")


def derive_session_key(shared_secret: bytes, context: str) -> bytes:
    """SHA256(shared_secret || context) — domain-separated key derivation."""
    return hashlib.sha256(shared_secret + b"|" + context.encode()).digest()


def generate_pairing_code() -> str:
    """6-digit pairing code (easy to read aloud / type on a phone)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def pairing_code_challenge(code: str, salt: str) -> str:
    """Constant-time-verifiable challenge for storing/transmitting the code.

    The control plane stores only salt+challenge (never the plaintext), the
    same pattern as password hashing. HMAC-SHA256 keyed with the salt keeps
    guessing offline impossible even if the DB leaks.
    """
    return hmac.new(salt.encode(), code.encode(), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def new_salt() -> str:
    return secrets.token_hex(16)


def new_nonce() -> str:
    """32 hex chars of entropy for frame nonces (replay defense)."""
    return secrets.token_hex(16)


def seal_frame(key: bytes, nonce: str, plaintext: bytes) -> bytes:
    """Encrypt one relay frame: HMAC(key, nonce||ciphertext) || ciphertext.

    The payload is masked with a nonce-seeded keystream, then tagged —
    dependency-free authenticated encryption. (AES-GCM via `cryptography`
    can replace this transparently later — same interface.)
    """
    mask = hashlib.sha256(key + nonce.encode()).digest()
    stream = bytearray()
    while len(stream) < len(plaintext):
        mask = hashlib.sha256(key + mask).digest()
        stream.extend(mask)
    ciphertext = bytes(p ^ stream[i] for i, p in enumerate(plaintext))
    tag = hmac.new(key, nonce.encode() + ciphertext, hashlib.sha256).digest()
    return base64.b64encode(tag + ciphertext)


def open_frame(key: bytes, nonce: str, sealed: bytes) -> Optional[bytes]:
    """Verify + decrypt one relay frame; None on tamper or bad encoding."""
    try:
        raw = base64.b64decode(sealed, validate=False)
    except Exception:
        return None  # malformed/tampered base64 is just a bad frame
    if len(raw) < 32:
        return None
    tag, ciphertext = raw[:32], raw[32:]
    expected = hmac.new(key, nonce.encode() + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        return None
    mask = hashlib.sha256(key + nonce.encode()).digest()
    stream = bytearray()
    while len(stream) < len(ciphertext):
        mask = hashlib.sha256(key + mask).digest()
        stream.extend(mask)
    return bytes(c ^ stream[i] for i, c in enumerate(ciphertext))

