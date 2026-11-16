# NEXUS Online Access — Control Plane + Node Deployment Guide

You can log in from anywhere while your personal data stays on your own
machines. Two tiers make this work:

```
┌─────────────────────────┐        ┌──────────────────────────────────┐
│  CONTROL PLANE (cloud)  │        │  NODE (your Mac or Windows PC)   │
│  Render free tier       │        │  runs the full NEXUS Core        │
│  auth + node registry   │◀──────▶│  holds ALL personal data         │
│  NO personal data       │claim/  │  tasks/notes/files/AI pipeline   │
│  Postgres: Neon/Supabase│heart-  │  SQLite on your own disk         │
│  always online          │beat    │  online when the machine is on   │
└─────────────────────────┘        └──────────────────────────────────┘
        ▲                                           ▲
        │ login from anywhere                       │ direct API when local
        └────────────── any device ─────────────────┘
```

- **Control plane** (this repo's control-plane mode): always-on,
  minimal — user accounts, device registry, node registry, activity log.
  Nothing else. It cannot serve your tasks/notes/files because those routers
  are not mounted in that mode (`NEXUS_CONTROL_PLANE_MODE=true`).
- **Node**: your Mac/Windows machine running the full Core. When it is
  online it *claims* the active slot; clients resolve it and talk to it
  directly for real work. When it goes offline the control plane keeps
  login working and resolution returns null until a machine returns.

## Data policy (what is stored where)

| Data | Control plane (cloud) | Node (your machine) |
| --- | --- | --- |
| Email + password hash | yes (auth) | yes (same account works) |
| Device/node registry, endpoints | yes | — |
| Activity log (action names, no content) | yes | yes |
| Projects / tasks / notes | **never** | yes |
| Files, inbox items, transcripts | **never** | yes |
| Sync payloads (content) | **never** | yes |

## Part 1 — Deploy the control plane on Render (free tier)

### 1. Get a free Postgres database

Pick either (both have a free tier):

- **Neon** (recommended): neon.tech → sign up → create project → copy the
  *pooled* connection string, e.g.
  `postgresql://user:pass@ep-xyz-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require`
- **Supabase**: supabase.com → new project → Settings → Database →
  Connection string → URI (use the *pooler* / port 6543 string for
  serverless-style workloads).

### 2. Push this repo to GitHub

```bash
cd <repo>
git push origin main
```

### 3. Create the Render service

1. Render dashboard → **New → Blueprint** → select the `nexus` repo.
   Render reads `services/core-api/render.yaml` and creates
   `nexus-control-plane` (free plan, Docker, health check `/health`).
2. First deploy will fail health checks until env vars are set — that's
   fine. Open the service → **Environment** and add:

   | Key | Value |
   | --- | --- |
   | `NEXUS_CONTROL_PLANE_MODE` | `true` (already in render.yaml) |
   | `NEXUS_DATABASE_URL` | your Neon/Supabase URL |
   | `NEXUS_JWT_SECRET` | output of `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `NEXUS_CORS_ORIGINS` | `["https://<your-service>.onrender.com"]` |
   | `NEXUS_STORAGE_ROOTS` | `[]` (already in render.yaml) |

3. **Manual deploy** once. Check `https://<your-service>.onrender.com/health`
   → `{"status": "ok", "mode": "control-plane", ...}`.

> **Why the pinned JWT secret?** Render's free filesystem is ephemeral — a
> generated secret would be regenerated on every deploy/restart and log you
> out. Pinning `NEXUS_JWT_SECRET` keeps tokens valid across deploys.

## Part 2 — Point the CLI at the control plane

On any machine (this is the "log in from anywhere" part):

```bash
cd apps/cli
pip install -r requirements.txt

nexus cp set https://<your-service>.onrender.com
nexus register --email you@example.com    # or create the account once
nexus cp login --email you@example.com    # prompts for password
nexus whoami                              # works from any network
```

## Part 3 — Promote your Mac/Windows machine to the main server

On the machine that should hold personal data:

```bash
# 1. Run the full Core locally (node mode = default)
cd services/core-api
pip install -r requirements.txt
python -m uvicorn nexus_core.main:app --host 0.0.0.0 --port 8000

# 2. In a second terminal, claim the active-node slot on the control plane
cd ../apps/cli
nexus cp set https://<your-service>.onrender.com
nexus cp login --email you@example.com
nexus node claim --name "MacBook Pro" --platform macos \
    --endpoint http://<your-lan-ip>:8000
# → this machine is now the active main server; any other node is demoted

# 3. Keep the claim alive (heartbeat every 30s; Ctrl-C stops)
nexus node claim --name "MacBook Pro" --watch
```

Other clients then resolve where the real server is:

```bash
nexus node resolve          # → active node + endpoint (or null if offline)
nexus node list             # all nodes with online/offline
```

One heartbeat every 30 s keeps the node within the 90 s freshness window;
if heartbeats stop, `nexus node resolve` returns null and clients fall back
to the control plane until a machine claims again.

### Reaching the node from outside the LAN (free options)

The node's `endpoint` is whatever clients can reach:

| Method | Setup | Cost |
| --- | --- | --- |
| **Tailscale** (recommended) | Install on node + phone/laptop; use the MagicDNS name, e.g. `http://mbp.tailnet-name.ts.net:8000` | free tier, 3 users / 100 devices |
| **Cloudflare Tunnel** | `cloudflared tunnel --url http://localhost:8000` on the node; paste the trycloudflare URL as endpoint | free, no account needed for quick tunnels |
| **ngrok** | `ngrok http 8000` | free tier (URL changes on restart) |
| LAN only | `http://<lan-ip>:8000` | works at home |

Claim with the chosen endpoint:

```bash
nexus node claim --name "MacBook Pro" --endpoint http://mbp.tail1234.ts.net:8000
```

## Part 4 — Install node services (transcription etc.)

With the node running, install optional services on it:

```bash
nexus services status            # what's installed (stt, llm)
nexus services install stt        # faster-whisper via pip
nexus services install llm        # instructions for Ollama
```

- **STT**: `faster-whisper` (pip) — reliable local transcription; the
  `base` model (~150 MB) downloads on first use, `small` (~460 MB) is more
  accurate. The inbox pipeline uses it automatically when installed
  (`POST /api/inbox/audio`).
- **LLM**: install Ollama natively from <https://ollama.com/download>, then
  `ollama pull llama3.2`. The intent extractor auto-detects it at
  `127.0.0.1:11434`.

`nexus services install` reports what it finds to the control plane, so
`nexus node resolve` shows which node has STT available.

## Free-tier services used

| Service | Role | Free tier (as of writing) |
| --- | --- | --- |
| Render | control-plane API hosting | 750 h/month, sleeps after 15 min idle |
| Neon | Postgres (control-plane DB) | 0.5 GB, autosuspend |
| Supabase | Postgres alternative | 500 MB, pauses after 1 week idle |
| GitHub | source + CI (`.github/workflows/ci.yml`) | unlimited public repos |
| Tailscale | private network to the node | personal tier free |
| Cloudflare Tunnel | public URL to the node | free |

Free-tier caveats worth knowing: Render spins down after ~15 min idle (first
request after that takes ~30 s to wake); Neon autosuspends (first query pays
a cold start); Supabase pauses a project after a week of inactivity (bring it
back from the dashboard). None of these affect the node — local-first.

## Vercel note

Vercel is for the (future) web frontend, not the Python control plane: it
runs serverless functions (Node/Python) without long-lived WebSockets, and
the desktop/mobile clients need a stable API origin. The control plane runs
on Render; when a browser dashboard lands, its static build can go to
Vercel with `NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com`.

## Operations cheat sheet

```bash
# Control plane health (from anywhere)
curl https://<your-service>.onrender.com/health

# Am I talking to the control plane or a node?
curl <api-origin>/health        # → "mode": "control-plane" | "node"

# Rotate the node api_key (also re-activates the node)
nexus node claim --name "MacBook Pro" --endpoint http://mbp.tail1234:8000

# Remove a stale node entirely
nexus node list                 # find the id
curl -X DELETE https://<cp>/api/nodes/<id> -H "Authorization: Bearer <token>"
```

The full walkthrough with screenshots-level detail is in
`NEXUS_Online_Access_Guide.docx` in the project downloads.
