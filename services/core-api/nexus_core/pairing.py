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
   control plane with ChaCha20Poly1305 AEAD and direction-separated keys).
   The control plane routes frames without ability to inspect or forge
   plaintext.

4. AUTHORIZATION: relayed requests run through the node's normal FastAPI
   stack — the device's scoped token is enforced there, so ownership
   filtering and scope checks apply exactly as on the LAN.

Routes live in routers/relay.py; crypto helpers here.
"""
import base64
import hashlib
import hmac
import secrets
from typing import Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# ---------------------------------------------------------------------------
# X25519 (RFC 7748) — pure Python Montgomery ladder.
# The test suite cross-verifies against the `cryptography` package.
# ---------------------------------------------------------------------------
P = 2**255 - 19
_A24 = 121665


def _x25519_mult(k: int, u: int) -> int:
    """Scalar multiplication on Curve25519 (Montgomery ladder, RFC 7748)."""
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
    """Derive a 32-byte key using HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=context.encode("utf-8"),
    )
    return hkdf.derive(shared_secret)


def derive_direction_keys(shared_secret: bytes, transcript: bytes = b"") -> tuple[bytes, bytes]:
    """Derive distinct direction keys via HKDF-SHA256 (dev->node and node->dev).
    
    Prevents key/nonce reuse across directions.
    """
    salt = hashlib.sha256(transcript).digest() if transcript else b"nexus-relay-v2-salt"
    k_dev_to_node = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"dev>node:nexus-relay-v2",
    ).derive(shared_secret)

    k_node_to_dev = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"node>dev:nexus-relay-v2",
    ).derive(shared_secret)

    return k_dev_to_node, k_node_to_dev


def generate_pairing_code() -> str:
    """6-digit pairing code (easy to read aloud / type on a phone)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def pairing_code_challenge(code: str, salt: str) -> str:
    """Constant-time-verifiable challenge for storing/transmitting the code."""
    return hmac.new(salt.encode(), code.encode(), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def new_salt() -> str:
    return secrets.token_hex(16)


def new_nonce() -> str:
    """24 hex chars (12 bytes) of entropy for ChaCha20Poly1305 frame nonces."""
    return secrets.token_hex(12)


def _normalize_nonce(nonce: str | bytes) -> bytes:
    """Normalize input nonce to 12 bytes for ChaCha20Poly1305."""
    if isinstance(nonce, str):
        try:
            raw = bytes.fromhex(nonce)
            if len(raw) >= 12:
                return raw[:12]
        except ValueError:
            pass
        return hashlib.sha256(nonce.encode("utf-8")).digest()[:12]
    if isinstance(nonce, bytes):
        if len(nonce) == 12:
            return nonce
        if len(nonce) > 12:
            return nonce[:12]
        return hashlib.sha256(nonce).digest()[:12]
    raise ValueError(f"Invalid nonce type: {type(nonce)}")


def seal_frame(key: bytes, nonce: str | bytes, plaintext: bytes) -> bytes:
    """Encrypt one relay frame using ChaCha20Poly1305 AEAD.
    
    Returns base64-encoded ciphertext + 16-byte Poly1305 tag.
    """
    n_bytes = _normalize_nonce(nonce)
    chacha = ChaCha20Poly1305(key)
    ciphertext_and_tag = chacha.encrypt(n_bytes, plaintext, None)
    return base64.b64encode(ciphertext_and_tag)


def open_frame(key: bytes, nonce: str | bytes, sealed: bytes) -> Optional[bytes]:
    """Verify + decrypt one relay frame using ChaCha20Poly1305 AEAD.
    
    Returns decrypted plaintext or None if tampered or invalid.
    """
    try:
        raw = base64.b64decode(sealed, validate=False)
        n_bytes = _normalize_nonce(nonce)
        chacha = ChaCha20Poly1305(key)
        return chacha.decrypt(n_bytes, raw, None)
    except (InvalidTag, Exception):
        return None
