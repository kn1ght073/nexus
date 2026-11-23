"""NEXUS Core API application entry point.

Replaces the flat main.py: app factory, locked-down CORS (was
allow_origins=["*"] with credentials — invalid and unsafe), WebSocket
event channel, and the /health probe the CLI pings.

Two deployment modes (see docs/deploy/online-access.md):
- full node (default): every router; runs on your own machine, holds
  personal data on its own disks.
- control plane (NEXUS_CONTROL_PLANE_MODE=true): mounts ONLY auth, devices,
  activity, nodes and the relay — the coordination surface for "log in from
  anywhere". Personal data (projects/tasks/notes/files/inbox/sync) never
  mounts there.

Public-internet hardening applied here:
- /docs and /openapi.json hidden unless NEXUS_EXPOSE_DOCS=true (an open
  schema is a roadmap for attackers; enable locally while developing).
- Security headers on every response (OWASP core set).
- Request body cap (default 10 MB) so one client cannot exhaust memory on
  a 512 MB free instance.
- /health answers with the minimum a probe needs.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.staticfiles import StaticFiles

from .database import Base, SessionLocal, engine, get_db
from .events import DomainEvent, subscribe, unsubscribe
from .models import User
from .routers import all_routers
from .security import decode_token, get_current_user
from .settings import get_settings

settings = get_settings()

# Routers safe for the hosted control plane: identity + coordination only.
# "relay" is the port-free bridge between devices and the node (routers/relay.py).
CONTROL_PLANE_ROUTES = ("auth", "devices", "activity", "nodes", "relay", "account")


def _ensure_schema_compatibility(db_engine):
    """Safely apply non-destructive column additions on existing PostgreSQL databases."""
    url_str = str(db_engine.url)
    if "postgresql" in url_str or "postgres" in url_str:
        from sqlalchemy import text
        with db_engine.connect() as conn:
            for stmt in (
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) DEFAULT 'user' NOT NULL;",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(255);",
                "ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;",
                "ALTER TABLE external_identities ADD COLUMN IF NOT EXISTS picture_url VARCHAR(1024);",
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS family_id VARCHAR(64);",
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS created_via VARCHAR(32) DEFAULT 'password';",
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS last_used_ip VARCHAR(64);",
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_agent VARCHAR(512);",
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS rotated_at TIMESTAMP;",
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP;",
            ):
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass
            conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables at boot (SQLite WAL is set per-connection in database.py)
    Base.metadata.create_all(bind=engine)
    _ensure_schema_compatibility(engine)
    yield


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """OWASP secure-headers core set on every response (pure wins, no config)."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        # HSTS only makes sense behind real TLS (Render/self-hosted Caddy
        # terminate it upstream); harmless on plain localhost anyway.
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject bodies larger than settings.max_body_bytes with 413 (both declared and chunked/streaming)."""

    async def dispatch(self, request: Request, call_next):
        max_bytes = get_settings().max_body_bytes
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            return JSONResponse({"detail": "Payload too large"}, status_code=413)

        # For chunked or undeclared content-length, wrap the receive callable to enforce budget
        received = 0
        original_receive = request.receive

        async def receive_with_cap():
            nonlocal received
            message = await original_receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    raise HTTPException(status_code=413, detail="Payload too large")
            return message

        request._receive = receive_with_cap
        try:
            return await call_next(request)
        except HTTPException as exc:
            if exc.status_code == 413:
                return JSONResponse({"detail": "Payload too large"}, status_code=413)
            raise


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
        # Hide the interactive docs and schema on the public internet;
        # flip NEXUS_EXPOSE_DOCS=true in your dev .env to get them back.
        docs_url="/docs" if settings.expose_docs else None,
        redoc_url="/redoc" if settings.expose_docs else None,
        openapi_url="/openapi.json" if settings.expose_docs else None,
    )

    # CORS: explicit origins only.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.effective_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/health", tags=["system"])
    def health_check():
        # Minimum a probe needs: is it up, and which mode answers. The
        # version string is deliberately absent on the public internet.
        return {
            "status": "ok",
            "service": "nexus-core",
            "mode": mode,
        }

    @app.get("/api/system/status", tags=["system"])
    def system_status(
        db: SessionLocal = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        """Authenticated operator infrastructure status probe."""
        import time
        from sqlalchemy import text

        # Check DB latency
        t0 = time.perf_counter()
        db_ok = False
        db_err = None
        try:
            db.execute(text("SELECT 1")).scalar()
            db_ok = True
        except Exception as e:
            db_err = str(e)
        db_ms = round((time.perf_counter() - t0) * 1000, 2)

        is_owner = getattr(current_user, "role", "user") == "owner"

        return {
            "service": "nexus-control-plane",
            "mode": mode,
            "database": {
                "status": "connected" if db_ok else "degraded",
                "latency_ms": db_ms,
                "engine": "postgresql" if settings.database_url else "sqlite",
                "error": db_err if is_owner else None,
            },
            "auth": {
                "password_auth_allowed": settings.is_password_auth_allowed,
                "google_oidc_configured": bool(settings.google_client_id),
                "google_allowlist_active": bool(settings.allowed_google_emails),
            },
            "node_coordination": {
                "heartbeat_timeout_sec": settings.node_heartbeat_timeout,
                "relay_enabled": settings.relay_enabled,
                "pairing_ttl_sec": settings.pairing_code_ttl,
            },
            "operator": {
                "user_id": current_user.id,
                "email": current_user.email,
                "role": getattr(current_user, "role", "user"),
            },
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

    # --- Live Web Showcase & Operator Control Center Hosting ---
    showcase_dir = Path(__file__).parent / "showcase"
    web_dir = Path(__file__).parent / "web_ui"

    if showcase_dir.is_dir():
        app.mount("/showcase", StaticFiles(directory=str(showcase_dir)), name="showcase")

    if web_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(web_dir)), name="assets")

    @app.get("/", include_in_schema=False)
    def serve_showcase():
        if showcase_dir.is_dir() and (showcase_dir / "index.html").is_file():
            return FileResponse(showcase_dir / "index.html")
        elif web_dir.is_dir():
            return FileResponse(web_dir / "index.html")
        return {"status": "ok", "service": "nexus-core"}

    @app.get("/admin", include_in_schema=False)
    @app.get("/admin/", include_in_schema=False)
    def serve_admin():
        if web_dir.is_dir() and (web_dir / "index.html").is_file():
            return FileResponse(web_dir / "index.html")
        raise HTTPException(status_code=404, detail="Control center interface not installed")

    @app.get("/client", include_in_schema=False)
    @app.get("/client/", include_in_schema=False)
    def serve_client():
        if web_dir.is_dir() and (web_dir / "client.html").is_file():
            return FileResponse(web_dir / "client.html")
        raise HTTPException(status_code=404, detail="Client console interface not installed")

    @app.get("/console", include_in_schema=False)
    @app.get("/dashboard", include_in_schema=False)
    def redirect_to_admin():
        return RedirectResponse(url="/admin", status_code=307)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("nexus_core.main:app", host=settings.host, port=settings.port, reload=False)
