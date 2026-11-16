"""NEXUS Core API application entry point.

Replaces the flat main.py: app factory, locked-down CORS (was
allow_origins=["*"] with credentials — invalid and unsafe), WebSocket
event channel, and the /health probe the CLI pings.

Two deployment modes (see docs/deploy/online-access.md):
- full node (default): every router; runs on your own machine, holds
  personal data on its own disks.
- control plane (NEXUS_CONTROL_PLANE_MODE=true): mounts ONLY auth, devices,
  activity and nodes — the coordination surface for "log in from anywhere".
  Personal data (projects/tasks/notes/files/inbox/sync) never mounts there.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine
from .events import DomainEvent, subscribe, unsubscribe
from .routers import all_routers
from .security import decode_token
from .settings import get_settings

settings = get_settings()

# Routers safe for the hosted control plane: identity + coordination only.
CONTROL_PLANE_ROUTES = ("auth", "devices", "activity", "nodes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables at boot (SQLite WAL is set per-connection in database.py)
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    mode = "control-plane" if settings.control_plane_mode else "node"
    app = FastAPI(
        title="NEXUS Core API",
        description=(
            "Central API Node for the NEXUS Personal Digital Infrastructure"
            + (" (control plane: auth + coordination only)" if settings.control_plane_mode else "")
        ),
        version="0.3.0",
        lifespan=lifespan,
    )

    # CORS: explicit origins only. The old config combined allow_origins=["*"]
    # with allow_credentials=True, which browsers reject outright.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health", tags=["system"])
    def health_check():
        return {
            "status": "ok",
            "service": "nexus-core",
            "version": "0.3.0",
            "mode": mode,
        }

    if settings.control_plane_mode:
        # Coordination surface only: filter to the safe routers by prefix.
        mounted = []
        for router in all_routers:
            prefix = (router.prefix or "").strip("/")
            if prefix in CONTROL_PLANE_ROUTES:
                app.include_router(router, prefix="/api")
                mounted.append(prefix)
        assert set(mounted) == set(CONTROL_PLANE_ROUTES), (
            f"control-plane mount mismatch: {mounted} vs {CONTROL_PLANE_ROUTES}"
        )
    else:
        for router in all_routers:
            app.include_router(router, prefix="/api")

    @app.websocket("/ws")
    async def websocket_events(websocket: WebSocket):
        """Live event channel. Auth: access token in the first message."""
        import asyncio

        await websocket.accept()
        user_id: int | None = None
        queue = None
        pump: asyncio.Task | None = None
        try:
            # -- authenticate with the first frame --
            token = (await websocket.receive_text()).strip()
            try:
                payload = decode_token(token, expected_type="access")
                user_id = int(payload["sub"])
            except Exception:
                await websocket.send_json({"type": "error", "detail": "invalid token"})
                await websocket.close(code=1008)
                return

            queue = subscribe()

            async def event_pump() -> None:
                while True:
                    event = await queue.get()
                    if event.get("user_id") == user_id:
                        await websocket.send_json(event)

            pump = asyncio.create_task(event_pump())
            await websocket.send_json({"type": "ready", "user_id": user_id})

            # Block on client frames (heartbeats); disconnect raises here,
            # which also unblocks and cancels the pump.
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            try:
                await websocket.close()
            except Exception:
                pass
        finally:
            if pump is not None:
                pump.cancel()
            if queue is not None:
                unsubscribe(queue)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("nexus_core.main:app", host=settings.host, port=settings.port, reload=False)
