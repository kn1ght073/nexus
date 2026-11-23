"""Secure relay: devices talk to the user's node through the control plane.

Why: the node (the machine with your data) sits behind NAT. This router
gives it a global presence WITHOUT opening a single inbound port:

  node ── outbound WebSocket ──▶ /api/relay/{node_id}/ws  (node api_key)
  device ── WebSocket ────────▶ /api/relay/attach        (pairing code)

The control plane routes frames between the two sockets and cannot read
them: the DEVICE and the NODE run an X25519 ECDH handshake through the
first relayed frame (public keys only), deriving a session key that never
leaves the endpoints (pairing.py). Relay = routing, not trust.

Frame protocol (JSON over both sockets, after the attach handshake):

  device→node : {"v":1,"id":"<corr-id>","nonce":"<hex>",
                 "payload":<sealed JSON request>}
    request  = {"method","path","query","headers","body_b64"}
  node→device : same shape, sealed response {"status","headers","body_b64"}

  Sealing: seal_frame(session_key, nonce, request_json) — authenticated
  encryption; per-frame nonce + replay window on both ends.

Authorization: the node unwraps the request and runs it through its own
FastAPI app with the device's Bearer token — ownership filters and scope
checks apply exactly as if the device were on the LAN. The control plane
never sees a token or a plaintext body.
"""
import asyncio
import json
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from .. import pairing as crypto
from ..database import get_db, SessionLocal
from ..deps import log_activity
from ..models import Device, Node, PairingSession, RelayLink, User, utcnow
from ..ratelimit import RateLimiter
from ..schemas import (
    NodeOut,
    PairingCodeRequest,
    PairingCodeResponse,
    PairingCompleteRequest,
    PairingCompleteResponse,
)
from ..security import create_token, get_current_user
from ..settings import get_settings

router = APIRouter(prefix="/relay", tags=["relay"])
settings = get_settings()

# Wrong pairing codes per session: 5 strikes and the session dies.
_pairing_limiter = RateLimiter(settings.pairing_max_attempts, settings.pairing_code_ttl)
# Attach handshakes per pairing session (each successful attach consumes it).
_attach_limiter = RateLimiter(3, settings.pairing_code_ttl)


# ---------------------------------------------------------------------------
# In-process relay table (single worker; Redis when scaled out — see
# docs/deploy/online-access.md §"Scaling the control plane").
# ---------------------------------------------------------------------------
class RelayState:
    """node_id -> {"ws": ..., "owner_id": ..., "device": ... | None}

    The single active device attachment is stored with the node entry: one
    phone at a time relays through the socket, which keeps the frame pump
    trivially ordered. (Multiple concurrent devices = one socket each in
    a later iteration; the schema already supports it via RelayLink rows.)
    """

    def __init__(self) -> None:
        self.nodes: dict[int, dict] = {}
        self.lock = asyncio.Lock()

    async def register(self, node_id: int, ws: WebSocket, owner_id: int) -> dict | None:
        async with self.lock:
            old = self.nodes.get(node_id)
            if old:
                try:
                    await old["ws"].close(code=4000)
                except Exception:
                    pass
            entry = {"ws": ws, "owner_id": owner_id, "device": None}
            self.nodes[node_id] = entry
            return old

    async def unregister(self, node_id: int, ws: WebSocket) -> None:
        async with self.lock:
            current = self.nodes.get(node_id)
            if current and current["ws"] is ws:
                self.nodes.pop(node_id, None)

    def get(self, node_id: int) -> dict | None:
        return self.nodes.get(node_id)

    def connected_node_ids(self) -> list[int]:
        return list(self.nodes.keys())


relay_state = RelayState()


def _fresh(node: Node, connected: list[int] | None = None) -> bool:
    if node.last_seen is None:
        return False
    seen = node.last_seen.replace(tzinfo=None) if node.last_seen.tzinfo else node.last_seen
    if (utcnow().replace(tzinfo=None) - seen).total_seconds() < settings.node_heartbeat_timeout:
        return True
    return bool(connected and node.id in connected)


def _node_out(node: Node, connected: list[int] | None = None) -> Node:
    setattr(node, "is_online", _fresh(node, connected))
    return node


# ---------------------------------------------------------------------------
# Pairing REST endpoints (owner creates a code; device redeems it).
# ---------------------------------------------------------------------------
@router.post("/pair", response_model=PairingCodeResponse, status_code=status.HTTP_201_CREATED)
def create_pairing_code(
    request: PairingCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Owner-side: mint a 6-digit code good for `pairing_code_ttl` seconds.

    The plaintext is shown exactly once on the owner's screen; only the
    salted HMAC challenge is stored. Minting is throttled per user so a
    hostile account cannot flood the table, and stale pending sessions
    expire the moment a fresh one is minted.
    """
    if not _pairing_limiter.allow(f"mint:{current_user.id}"):
        raise HTTPException(status_code=429, detail="Too many pairing requests; wait a bit.")
    code = crypto.generate_pairing_code()
    salt = crypto.new_salt()
    session = PairingSession(
        owner_id=current_user.id,
        salt=salt,
        challenge=crypto.pairing_code_challenge(code, salt),
        device_name=request.device_name,
        expires_at=utcnow() + timedelta(seconds=settings.pairing_code_ttl),
    )
    db.add(session)
    db.query(PairingSession).filter(
        PairingSession.owner_id == current_user.id,
        PairingSession.status == "pending",
        PairingSession.expires_at < utcnow(),
    ).update({"status": "expired"}, synchronize_session=False)
    db.commit()
    db.refresh(session)
    log_activity(db, user_id=current_user.id, action="pairing.created", detail=f"session #{session.id}")
    db.commit()
    return PairingCodeResponse(
        pairing_id=session.id,
        code=code,
        expires_at=session.expires_at,
        relay_url="/api/relay/attach",
    )


def _validate_pairing(db: Session, pairing_id: int, code: str) -> tuple[PairingSession, int]:
    """Shared validation for the REST and WS attach paths.

    Returns (session, owner_id); raises the right status codes on failure
    and burns the session after too many wrong codes.
    """
    session = db.query(PairingSession).filter(PairingSession.id == pairing_id).first()
    if session is None or session.status != "pending":
        raise HTTPException(status_code=404, detail="Pairing session not found")
    if session.expires_at.replace(tzinfo=None) < utcnow().replace(tzinfo=None):
        session.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Pairing code expired")
    if not _pairing_limiter.allow(f"try:{session.id}"):
        session.status = "expired"
        db.commit()
        raise HTTPException(status_code=429, detail="Too many wrong codes; session closed.")
    if not crypto.constant_time_equals(
        crypto.pairing_code_challenge(code, session.salt), session.challenge
    ):
        session.attempts += 1
        if session.attempts >= settings.pairing_max_attempts:
            session.status = "expired"
        db.commit()
        raise HTTPException(status_code=401, detail="Wrong pairing code")
    return session, session.owner_id


@router.post("/attach", response_model=PairingCompleteResponse)
def complete_pairing(request: PairingCompleteRequest, db: Session = Depends(get_db)):
    """Device-side REST fallback: exchange the code for a scoped device token.

    Unauthenticated by design (the device has no account yet — the code IS
    the credential), but the validation is the strict one from
    _validate_pairing: pending, unexpired, constant-time code match, five
    strikes and dead. The response token carries scopes capture,read,sync;
    relaying that token to the node gives it exactly those powers.
    """
    session, owner_id = _validate_pairing(db, request.pairing_id, request.code)
    # Atomic transition from pending to completed (F13)
    rows = (
        db.query(PairingSession)
        .filter(PairingSession.id == session.id, PairingSession.status == "pending")
        .update({"status": "completed"}, synchronize_session=False)
    )
    db.commit()
    if rows != 1:
        raise HTTPException(status_code=409, detail="Pairing session already redeemed or completed")

    device = Device(
        name=request.device_name or "Paired device",
        platform=request.platform,
        capabilities="capture,read,sync",
        is_online=True,
        owner_id=owner_id,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    node = db.query(Node).filter(Node.owner_id == owner_id, Node.is_active.is_(True)).first()
    log_activity(db, user_id=owner_id, action="pairing.completed", detail=f"device #{device.id}")
    db.commit()
    return PairingCompleteResponse(
        device_id=device.id,
        token=create_token(owner_id, "access", device_id=device.id, scope="capture,read,sync"),
        node=_node_out(node, relay_state.connected_node_ids()) if node else None,
    )


# ---------------------------------------------------------------------------
# Node socket: outbound presence, request pump.
# ---------------------------------------------------------------------------
@router.websocket("/{node_id}/ws")
async def node_relay_socket(websocket: WebSocket, node_id: int, key: str = Query(...)):
    """The node's outbound presence on the control plane.

    Auth: the node api_key issued at claim (Query param — WebSocket
    handshake headers are awkward across browsers/CLIs). A second connect
    for the same node replaces the first socket (single node presence).

    After accept, the node receives device frames and replies with sealed
    responses computed locally (see nexus_core/node_bridge.py for the node
    half; this socket just moves bytes). "ping" frames keep NAT mappings
    warm and double as a super-heartbeat: a connected socket counts as
    fresh in /nodes/active.
    """
    db = SessionLocal()
    try:
        node = db.query(Node).filter(Node.id == node_id, Node.api_key == key).first()
        if node is None or not key:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        node.last_seen = utcnow()
        db.commit()
        owner_id = node.owner_id
    finally:
        db.close()
    await relay_state.register(node_id, websocket, owner_id)

    try:
        while True:
            frame = json.loads(await websocket.receive_text())
            op = frame.get("op")
            if op == "ping":
                await websocket.send_json({"op": "pong", "t": frame.get("t")})
                continue
            # Everything else from the NODE is a reply/handshake destined for
            # the attached device: forward verbatim (sealed bytes — we cannot
            # read them, by design).
            entry = relay_state.get(node_id)
            if entry and entry.get("device") is not None:
                device_ws = entry["device"]
                try:
                    await device_ws.send_text(json.dumps(frame))
                except Exception:
                    entry["device"] = None
    except WebSocketDisconnect:
        pass
    finally:
        await relay_state.unregister(node_id, websocket)
        db = SessionLocal()
        try:
            db.query(Node).filter(Node.id == node_id).update({"last_seen": utcnow()})
            db.commit()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Device socket: pair-then-attach, then pump sealed frames.
# ---------------------------------------------------------------------------
@router.websocket("/attach")
async def device_attach_socket(websocket: WebSocket):
    """Device side of the relay.

    Handshake (first frame): {"pairing_id":..,"code":"..","device_name":..,
    "platform":..} — validated exactly like POST /attach. On success the
    control plane links this socket to the node's socket and answers:
      {"ok":true,"device_id":..,"node":{...},"device_pubkey":null}
    then relays every subsequent text frame to the node socket verbatim
    and every node reply back here. The ECDH handshake + sealed traffic
    happen INSIDE those frames between device and node directly.
    """
    await websocket.accept()
    db = SessionLocal()
    device_id = None
    node_id = None
    try:
        try:
            raw_hello = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            hello = json.loads(raw_hello)
        except asyncio.TimeoutError:
            await websocket.send_json({"ok": False, "detail": "Handshake timed out"})
            await websocket.close(code=4408)
            return
        except Exception:
            await websocket.close(code=4400)
            return

        try:
            session, owner_id = _validate_pairing(db, hello.get("pairing_id", -1), hello.get("code", ""))
        except HTTPException as exc:
            await websocket.send_json({"ok": False, "detail": exc.detail})
            await websocket.close(code=4401)
            return
        if not _attach_limiter.allow(f"attach:{session.id}"):
            await websocket.send_json({"ok": False, "detail": "attach throttled"})
            await websocket.close(code=4429)
            return

        # Atomic transition from pending to completed (F13)
        rows = (
            db.query(PairingSession)
            .filter(PairingSession.id == session.id, PairingSession.status == "pending")
            .update({"status": "completed"}, synchronize_session=False)
        )
        db.commit()
        if rows != 1:
            await websocket.send_json({"ok": False, "detail": "Pairing session already redeemed"})
            await websocket.close(code=4409)
            return

        device = Device(
            name=hello.get("device_name") or "Paired device",
            platform=hello.get("platform", "android"),
            capabilities="capture,read,sync",
            is_online=True,
            owner_id=owner_id,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        device_id = device.id

        node = db.query(Node).filter(Node.owner_id == owner_id, Node.is_active.is_(True)).first()
        entry = relay_state.get(node.id) if node else None
        if node is None or entry is None:
            await websocket.send_json({"ok": False, "detail": "node offline"})
            await websocket.close(code=4403)
            return
        node_id = node.id
        if entry.get("device") is not None:
            # one device attachment at a time per node socket
            await websocket.send_json({"ok": False, "detail": "another device attached"})
            await websocket.close(code=4409)
            return
        entry["device"] = websocket
        db.add(RelayLink(owner_id=owner_id, node_id=node.id, device_id=device.id))
        log_activity(db, user_id=owner_id, action="relay.attached", detail=f"device #{device.id} → node #{node.id}")
        db.commit()
        await websocket.send_json({
            "ok": True,
            "device_id": device.id,
            "node": {"id": node.id, "name": node.name, "platform": node.platform},
        })

        # pure pipe: device frame -> node socket; node reply -> device
        try:
            while True:
                frame = await websocket.receive_text()
                try:
                    await entry["ws"].send_text(frame)
                except Exception:
                    await websocket.send_json({"op": "error", "detail": "node socket gone"})
                    break
        except WebSocketDisconnect:
            pass
        finally:
            entry["device"] = None
            db = SessionLocal()
            try:
                db.query(RelayLink).filter(
                    RelayLink.node_id == node_id, RelayLink.device_id == device_id,
                    RelayLink.detached_at.is_(None),
                ).update({"detached_at": utcnow()}, synchronize_session=False)
                db.commit()
            finally:
                db.close()
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        db.close()
