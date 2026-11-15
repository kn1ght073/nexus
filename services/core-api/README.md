# NEXUS Core API — `nexus_core/`

The central API Node of the NEXUS ecosystem (the "basic core handling
component" of the architecture plan). Runs on the Windows Node; serves the
Desktop, CLI, and Android clients over the local network.

## Stack

FastAPI 0.128 · Uvicorn · SQLAlchemy 2.x · SQLite (WAL) · Pydantic v2 ·
Argon2id (passwords) · PyJWT (tokens) · WebSocket (live events)

## Layout

```text
nexus_core/
├── main.py          # app factory, CORS, /health, WebSocket /ws
├── settings.py      # NEXUS_* env config (DB path, storage roots, CORS)
├── database.py      # engine + WAL + FK pragmas
├── models.py        # User, Device, Project, Task, Note, Activity
├── schemas.py       # Pydantic request/response models
├── security.py      # Argon2 + JWT access/refresh, get_current_user
├── events.py        # in-process event bus (publish/subscribe)
├── deps.py          # ownership helpers, activity logging
└── routers/
    ├── auth.py      # register / login / refresh / me
    ├── devices.py   # register / list / heartbeat / remove
    ├── projects.py  # CRUD + soft-delete (tombstones)
    ├── tasks.py     # CRUD + /today + /done + soft-delete
    ├── notes.py     # CRUD + soft-delete
    ├── files.py     # browse + search, jailed to storage roots
    ├── activity.py  # append-only activity timeline
    └── sync.py      # /sync/pull incremental change feed
```

## Run

```bash
pip install -r requirements.txt
uvicorn nexus_core.main:app --reload          # dev (127.0.0.1:8000)
NEXUS_HOST=0.0.0.0 uvicorn nexus_core.main:app # LAN deployment
```

Docs: <http://127.0.0.1:8000/docs>

## Configuration (NEXUS_* env vars)

| Variable | Default | Purpose |
|---|---|---|
| `NEXUS_HOST` | `127.0.0.1` | bind address; `0.0.0.0` for LAN |
| `NEXUS_PORT` | `8000` | listen port |
| `NEXUS_DATABASE_PATH` | `nexus.db` | SQLite file location |
| `NEXUS_JWT_SECRET_FILE` | `nexus_jwt_secret` | persisted token-signing secret |
| `NEXUS_STORAGE_ROOTS` | `~/Documents` (JSON array) | file-jail roots for /files |
| `NEXUS_ACCESS_TOKEN_MINUTES` | `30` | access token TTL |
| `NEXUS_CORS_ORIGINS` | tauri + vite dev | allowed browser origins |

## Tests

```bash
python -m pytest tests/ -q    # 28 tests: auth, isolation, jail, WS, sync
```
