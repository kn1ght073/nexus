# NEXUS — Personal Digital Infrastructure

A unified personal computing ecosystem for managing work, files, devices, media,
automation, and local AI across Windows, macOS, Android, and the terminal —
**fully inside your local network**.

## Repository layout

```text
nexus/
├── apps/
│   ├── cli/          # NEXUS CLI (minor project 1) — Python, Typer + Rich + Textual
│   ├── desktop/      # NEXUS Desktop (major project) — planned
│   └── mobile/       # NEXUS Mobile (minor project 2) — planned
├── services/
│   └── core-api/     # NEXUS Core API — FastAPI + SQLAlchemy + SQLite (implemented)
├── docs/             # architecture, proposals, and implementation plans
└── tests/            # per-service test suites
```

## Quick start

### 1. Start the Core (the Windows Node's brain)

```bash
cd services/core-api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn nexus_core.main:app --reload                # dev: 127.0.0.1:8000
# LAN deployment (macOS/Android/CLI from other machines):
#   NEXUS_HOST=0.0.0.0 uvicorn nexus_core.main:app  + firewall rule for the private profile
```

Interactive API docs: `http://127.0.0.1:8000/docs` · Health probe: `http://127.0.0.1:8000/health`

### 2. Connect the CLI

```bash
cd apps/cli
pip install -r requirements.txt
pip install -e .            # installs the global `nexus` command
nexus init --url http://127.0.0.1:8000
nexus register               # first account (password 8+ chars)
nexus login                  # stores the token; all commands use it
nexus status                 # health + login state
nexus project create "Networking"
nexus task add "Finish report" 1
nexus task done 1
nexus task today
nexus devices
nexus ui                     # full-screen TUI
```

### 3. Run the tests

```bash
cd services/core-api && python -m pytest tests/ -q
```

## Online access (control plane + secure relay)

Log in from anywhere, promote any machine as your main server, and pair
phones with **zero open ports** — full guide:
[`docs/deploy/online-access.md`](docs/deploy/online-access.md).

```bash
# one-time setup — the app sets up its own environment (uv when present,
# pip otherwise; mirrors for slow links). No manual pip/venv/uv steps.
nexus bootstrap                    # or: nexus bootstrap --mirror tuna

# control plane (hosted on Render free tier, or self-hosted via docker compose)
nexus cp set https://<control-plane-url>      # then: nexus cp login

# promote THIS machine as the main server (any user, any OS)
nexus node claim --name "My Windows Box"     # claim + api_key + secure bridge

# pair a phone (shows a 6-digit code; type it into the app)
nexus node pair

# optional local AI services
nexus services status
nexus services install stt                   # faster-whisper (voice notes)
```

The control plane holds accounts and coordination only — never tasks,
notes, files, or transcripts. Devices reach the node through an
end-to-end-sealed relay (X25519 ECDH); the relay host cannot read
frames. Public-internet hardening: login throttling, account lockout,
hidden API docs, security headers, request-size caps.

## Architecture

Three interfaces (Desktop, CLI, Android) consume one **NEXUS Core API** hosted
on the Windows Node — one data model, one source of truth, everything local.

See `docs/architecture/` for the full picture, `docs/proposals/` for the
three project scopes, and `docs/plans/` for implementation slices.

## Security posture

- Real authentication: Argon2id password hashing + JWT access/refresh tokens
- Every query ownership-filtered; per-user isolation is enforced, not implied
- File browsing/search is jailed to configured storage roots (`NEXUS_STORAGE_ROOTS`)
- CORS locked to explicit origins; WebSocket requires an access token
- No telemetry, no cloud services, no data leaving the local network

## License

Personal academic project — not for redistribution.
