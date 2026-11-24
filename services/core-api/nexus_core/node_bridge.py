"""Node bridge: the module that turns a local Core into a global main server.

Runs INSIDE the node process (import from nexus_core.main's lifespan, or
standalone via `python -m nexus_core.node_bridge`). Responsibilities:

1. DIAL: one outbound WebSocket to the control plane relay, authenticated
   with the node api_key. Because it is outbound, the machine opens ZERO
   inbound ports — no port forwarding, no firewall holes, no public IP.

2. ECDH: when a paired device attaches, the first frame it sends is the
   handshake {"op":"e2e","device_pubkey":...}. The bridge answers with its
   own ephemeral public key; both sides derive the same session key
   (pairing.x25519). The control plane saw only public keys.

3. SERVE: sealed frames after that carry normal HTTP requests. The bridge
   unwraps them and executes through the node's OWN FastAPI app — so every
   ownership filter, scope check, and rate limit applies as if the request
   arrived on the LAN. Sealed responses go back over the same socket.

4. HEARTBEAT: the socket pings double as heartbeats (a connected socket
   counts as fresh in /nodes/active), and the bridge keeps them warm.

5. INSTALLS: exposes local service installers (STT faster-whisper, LLM
   Ollama) so the desktop app can prompt "this node lacks transcription —
   install now?" and drive it over the relay (see routers/services.py).

The bridge is transport-only. It holds no credentials beyond the node
api_key and the ephemeral ECDH private (in memory, zeroized after the
handshake).
"""
import asyncio
import base64
from collections import deque
import hashlib
import hmac
import json
import time
from typing import Any

from . import pairing as crypto
from .settings import get_settings

settings = get_settings()


class NodeBridge:
    """State machine for the node side of the relay."""

    def __init__(self, control_plane_url: str, node_id: int, api_key: str, app=None):
        self.cp_url = control_plane_url.rstrip("/")
        self.node_id = node_id
        self.api_key = api_key
        self.app = app  # the FastAPI app to execute relayed requests against
        self.key_dev_to_node: bytes | None = None
        self.key_node_to_dev: bytes | None = None
        self.session_key: bytes | None = None  # set after ECDH; legacy compatibility
        self.device_pubkey: bytes | None = None
        self.ephemeral_private: bytes | None = None
        self.seen_nonces: set[str] = set()
        self._nonces_order: deque[str] = deque(maxlen=1024)
        self.pending: dict[str, asyncio.Future] = {}
        self._ws = None
        self._task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._stopping = False

    # ------------------------------------------------------------------ dial
    async def run(self) -> None:
        """Connect and serve forever (reconnects with backoff)."""
        import websockets  # node requirement (already pinned for /ws events)

        url = f"{self.cp_url.replace('http', 'ws', 1)}/api/relay/{self.node_id}/ws?key={self.api_key}"
        backoff = 1
        while not self._stopping:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    self._ws = ws
                    backoff = 1
                    await self._serve(ws)
            except Exception:
                if self._stopping:
                    return
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)  # cap at one minute

    async def _serve(self, ws) -> None:
        loop = asyncio.get_running_loop()
        self._ping_task = loop.create_task(self._ping_loop(ws))
        try:
            async for message in ws:
                await self._on_frame(ws, message)
        finally:
            if self._ping_task:
                self._ping_task.cancel()

    async def _ping_loop(self, ws) -> None:
        """Keep NAT mappings warm + super-heartbeat."""
        while True:
            await asyncio.sleep(25)
            try:
                await ws.send(json.dumps({"op": "ping", "t": time.time()}))
            except Exception:
                return

    # ----------------------------------------------------------------- frames
    async def _on_frame(self, ws, message: str) -> None:
        frame = json.loads(message)
        op = frame.get("op")

        if op == "pong":
            return

        if op == "e2e":
            # Device's ephemeral public key arrives; reply with ours.
            self.device_pubkey = base64.b64decode(frame["device_pubkey"])
            self.ephemeral_private, node_pub = crypto.x25519_keypair()
            shared = crypto.x25519_shared(self.ephemeral_private, self.device_pubkey)
            if shared == b"\x00" * 32:
                await ws.send(json.dumps({"op": "e2e-reject", "detail": "bad key"}))
                return
            transcript = self.device_pubkey + node_pub
            self.key_dev_to_node, self.key_node_to_dev = crypto.derive_direction_keys(shared, transcript)
            self.session_key = self.key_node_to_dev
            self.ephemeral_private = None  # zeroize: never needed again
            self.seen_nonces.clear()
            self._nonces_order.clear()
            transcript_mac = hmac.new(self.api_key.encode("utf-8"), transcript, hashlib.sha256).hexdigest()
            await ws.send(json.dumps({
                "op": "e2e-ok",
                "node_pubkey": base64.b64encode(node_pub).decode(),
                "transcript_mac": transcript_mac,
            }))
            return

        if op == "req":
            await self._on_request(ws, frame)
            return

        if op == "proxy_req":
            req_id = frame.get("id")
            exec_payload = {
                "method": frame.get("method", "GET"),
                "path": frame.get("path", "/"),
                "headers": frame.get("headers", {}),
                "body_b64": frame.get("body_b64", ""),
            }
            res = await self._execute(exec_payload)
            await ws.send(json.dumps({
                "op": "proxy_res",
                "id": req_id,
                "status": res.get("status", 200),
                "headers": res.get("headers", {}),
                "body_b64": res.get("body_b64", ""),
            }))
            return

    async def _on_request(self, ws, frame: dict) -> None:
        """Unwrap a sealed request, execute it locally, seal the response."""
        if self.key_dev_to_node is None and self.session_key is None:
            await ws.send(json.dumps({"v": 1, "id": frame.get("id"), "op": "res",
                                      "error": "no session"}))
            return
        nonce = frame.get("nonce", "")
        if nonce in self.seen_nonces:
            await ws.send(json.dumps({"v": 1, "id": frame.get("id"), "op": "res",
                                      "error": "replay"}))
            return
        if len(self._nonces_order) == self._nonces_order.maxlen:
            oldest = self._nonces_order.popleft()
            self.seen_nonces.discard(oldest)
        self.seen_nonces.add(nonce)
        self._nonces_order.append(nonce)

        decrypt_key = self.key_dev_to_node or self.session_key
        raw = crypto.open_frame(decrypt_key, nonce, frame.get("payload", "").encode())
        if raw is None:
            await ws.send(json.dumps({"v": 1, "id": frame.get("id"), "op": "res",
                                      "error": "bad seal"}))
            return
        try:
            request = json.loads(raw)
        except ValueError:
            await ws.send(json.dumps({"v": 1, "id": frame.get("id"), "op": "res",
                                      "error": "bad json"}))
            return

        response = await self._execute(request)
        encrypt_key = self.key_node_to_dev or self.session_key
        res_nonce = crypto.new_nonce()
        sealed = crypto.seal_frame(
            encrypt_key, res_nonce, json.dumps(response).encode()
        ).decode()
        await ws.send(json.dumps({"v": 1, "id": frame.get("id"), "op": "res",
                                  "nonce": res_nonce, "payload": sealed}))

    # ------------------------------------------------------------- execution
    async def _execute(self, request: dict) -> dict:
        """Run one HTTP request through the local FastAPI app, ASGI-direct.

        The request carries the device's Authorization header — the node's
        dependency chain validates it exactly like a LAN request. Nothing
        here re-implements auth; that is the whole point.
        """
        if self.app is None:
            return {"status": 503, "headers": {}, "body_b64": ""}
        body = base64.b64decode(request.get("body_b64", "") or "")
        headers = [
            (k.lower().encode(), v.encode())
            for k, v in (request.get("headers") or {}).items()
            if k.lower() not in ("content-length", "transfer-encoding", "host")
        ]
        full_path = request.get("path", "/")
        if "?" in full_path:
            req_path, req_query = full_path.split("?", 1)
        else:
            req_path = full_path
            req_query = request.get("query") or ""

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": request.get("method", "GET"),
            "scheme": "http",
            "path": req_path,
            "raw_path": req_path.encode(),
            "query_string": req_query.encode(),
            "root_path": "",
            "headers": headers,
            "client": ("relay", 0),
            "server": ("node", 8000),
        }

        response = {"status": 500, "headers": {}, "body_b64": ""}
        request_sent = {"done": False}

        async def receive():
            if request_sent["done"]:
                return {"type": "http.disconnect"}
            request_sent["done"] = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            if message["type"] == "http.response.start":
                response["status"] = message["status"]
                response["headers"] = {
                    (k.decode() if isinstance(k, bytes) else k): (
                        v.decode() if isinstance(v, bytes) else v
                    )
                    for k, v in message.get("headers", [])
                }
            elif message["type"] == "http.response.body":
                current = base64.b64decode(response.get("body_b64", "") or "")
                response["body_b64"] = base64.b64encode(
                    current + message.get("body", b"")
                ).decode()

        try:
            await self.app(scope, receive, send)
        except Exception as exc:  # node-side failure must not kill the socket
            response = {"status": 500, "headers": {}, "body_b64": base64.b64encode(
                json.dumps({"detail": f"node error: {exc}"}).encode()).decode()}
        return response

    # ----------------------------------------------------------------- stop
    def stop(self) -> None:
        self._stopping = True
        if self._ping_task:
            self._ping_task.cancel()
        if self._task:
            self._task.cancel()


def bridge_from_settings(app=None):
    """Build a NodeBridge from node_bridge CLI/env config (NEXUS_BRIDGE_*).

    The desktop app / CLI sets these when the user picks "this machine as
    main server"; standalone `python -m nexus_core.node_bridge` reads them
    from the environment or the local nexus_node.json written at claim.
    """
    import json as _json
    from pathlib import Path

    cfg_path = Path("nexus_node.json")
    cfg = {}
    if cfg_path.exists():
        cfg = _json.loads(cfg_path.read_text(encoding="utf-8"))
    cp_url = cfg.get("control_plane_url") or settings.node_bridge_cp_url
    node_id = cfg.get("node_id") or settings.node_bridge_id
    api_key = cfg.get("api_key") or settings.node_bridge_key
    if not (cp_url and node_id and api_key):
        return None
    return NodeBridge(cp_url, node_id, api_key, app=app)


# --- module entrypoint ------------------------------------------------------
if __name__ == "__main__":
    import uvicorn  # noqa: F401

    async def _main():
        from .main import app

        bridge = bridge_from_settings(app=app)
        if bridge is None:
            print("node bridge not configured (nexus_node.json / NEXUS_BRIDGE_*)")
            return
        await bridge.run()

    asyncio.run(_main())
