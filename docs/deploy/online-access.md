# NEXUS Online Access — Control Plane, Node Promotion, Secure Relay

Log in from anywhere; keep personal data on your own machines; promote
**any** machine — yours, a family member's, a friend's — as the main
server; link phones to it with **zero open ports**; install AI services
in-app on demand.

```
┌──────────────────────────┐            ┌────────────────────────────────────┐
│   CONTROL PLANE (cloud)  │            │   NODE (any user's machine)        │
│   Render free tier OR    │◀─ outbound ─│   runs the full NEXUS Core         │
│   self-hosted (compose)  │   WebSocket │   holds ALL personal data          │
│   auth + node registry   │  (no ports)│   SQLite on its own disk           │
│   + pairing + RELAY      │            │   tasks/notes/files/AI pipeline    │
│   NO personal data       │            │   serves devices through the relay │
│   Postgres: Neon/Supabase│            │   + LAN/Tailscale when local       │
└──────────────────────────┘            └────────────────────────────────────┘
        ▲                                            ▲
        │ login / pairing codes                      │ sealed frames only
        └────────────────── any device ──────────────┘ (E2E encrypted via X25519)
```

- **Control plane** (`NEXUS_CONTROL_PLANE_MODE=true`): always-on,
  minimal — user accounts, device registry, node registry, pairing
  sessions, relay sockets, activity log of action names. Nothing else.
  Personal-data routers are not mounted; a test enforces 404s for all of
  them.
- **Node**: any user's Mac/Windows/Linux machine running the full Core.
  When its owner promotes it, it claims the active-node slot and dials
  the control plane with ONE outbound WebSocket. Because it is outbound,
  the node needs **no port forwarding, no public IP, no firewall holes**.
- **Relay**: devices reach their owner's node through the control plane
  with end-to-end sealed frames (X25519 ECDH between device and node —
  the control plane sees only public keys and ciphertext). The node runs
  each relayed request through its normal FastAPI stack: same ownership
  filters, same scopes, same rate limits, as if the caller were on the LAN.

## Data policy (what is stored where)

| Data | Control plane (cloud) | Node (your machine) |
| --- | --- | --- |
| Email + password hash | yes (auth) | yes (same account works) |
| Device/node registry, endpoints | yes | — |
| Pairing sessions (salted HMAC challenges only) | yes | — |
| Activity log (action names, no content) | yes | yes |
| Projects / tasks / notes | **never** | yes |
| Files, inbox items, transcripts | **never** | yes |
| Sync payloads (content) | **never** | yes |
| Relay frame bodies | **never** (routed, sealed) | decrypted on the node only |

## Public API security posture

The control plane is on the public internet, so the API assumes hostile
traffic by default:

| Threat | Defense |
| --- | --- |
| Password brute force | login throttled per (IP, email); account locks 5 min after 5 wrong passwords; locked accounts answer exactly like unknown ones (no account probing); Argon2 verification on unknown emails (timing equalizer) |
| Pairing code guessing | 6-digit codes, 10-minute TTL, single-use, salted-HMAC stored, 5 wrong codes kills the session |
| Replay | per-frame nonces + replay window on both ends of the relay |
| Frame tampering / MITM by the relay host | X25519 ECDH + HMAC-SHA256 authenticated encryption between device and node — the plane is an untrusted courier |
| Cross-user access | every query owner-filtered; pairing codes bind devices to their owner; 404 masking for absent resources |
| API surface discovery | /docs and /openapi.json hidden unless `NEXUS_EXPOSE_DOCS=true` |
| Clickjacking / sniffing / referrer leak | security headers (nosniff, frame-deny, no-referrer, HSTS) on every response |
| Memory exhaustion | 10 MB request body cap |
| Version fingerprinting | `/health` returns status + mode only |

Scale note: the rate-limit/lockout/relay tables are in-memory — correct
for one uvicorn worker (the Render free default). When scaling to
multiple workers, move them to the Postgres/Redis backing store; the
interfaces (`ratelimit.py`) are already isolated for that.

## Part 1 — Deploy the control plane

### Option A: Render (free tier)

1. **Postgres**: create a free database on **Neon** (recommended:
   autosuspend between bursts) or **Supabase**; copy the *pooled*
   connection string.
2. **Render**: New → Blueprint → this repo. `services/core-api/render.yaml`
   provisions `nexus-control-plane` (free plan, Docker, `/health`).
3. **Environment**:

   | Key | Value |
   | --- | --- |
   | `NEXUS_CONTROL_PLANE_MODE` | `true` (already in render.yaml) |
   | `NEXUS_DATABASE_URL` | your Neon/Supabase URL |
   | `NEXUS_JWT_SECRET` | `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `NEXUS_CORS_ORIGINS` | `["https://<your-service>.onrender.com"]` |

4. Manual deploy → check `/health` → `{"status": "ok", "mode": "control-plane"}`.

### Option B: self-hosted (open-source stack — zero vendor dependency)

The control plane is just this repo in a different mode; run it on any
always-on box (a mini PC, a NAS, a small VPS, a Raspberry Pi):

```bash
# on your server (Docker + Docker Compose installed)
git clone <this-repo> nexus && cd nexus/services/core-api
cp .env.example .env    # then edit the values below
docker compose up -d    # control plane + Postgres + Caddy TLS
```

`docker-compose.yml` (in this directory) brings up:

| Container | Role | Why |
| --- | --- | --- |
| `nexus-control-plane` | the API in control-plane mode | the code you are reading |
| `postgres` | Postgres 16 (official image) | accounts + coordination tables |
| `caddy` | automatic HTTPS via Let's Encrypt | TLS in front of the API |

Set in `.env`:

| Key | Value |
| --- | --- |
| `NEXUS_JWT_SECRET` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `NEXUS_DATABASE_URL` | `postgresql://nexus:<strong-password>@postgres:5432/nexus` |
| `NEXUS_CORS_ORIGINS` | `["https://<your-domain>"]` |
| `CADDY_DOMAIN` | the DNS name pointing at the server |

Open-source bonus: if you also want node↔device direct links without
even the relay, run **Headscale** (self-hosted Tailscale control server)
— nodes and phones join your private tailnet, talk peer-to-peer when
possible, and fall back to public relays. The relay in this repo covers
the same need without any third-party coordination at all.

## Part 2 — Any user, any machine: promote a main server

Each user does this on their own machine (all tools are built in — CLI
or desktop app; no port forwarding, no technical prerequisites):

```bash
# on the machine that should hold personal data
cd services/core-api
pip install -r requirements.txt
python -m uvicorn nexus_core.main:app --host 127.0.0.1 --port 8000   # node mode

# point at the control plane and claim the slot (multi-tenant: your slot only)
cd ../../apps/cli
nexus cp set https://<control-plane-url>
nexus cp login --email you@example.com
nexus node claim --name "My Windows Box"     # auto: platform, api_key, bridge
```

`claim` now also starts the **secure bridge** (or writes
`nexus_node.json` for `python -m nexus_core.node_bridge`): the outbound
relay socket that gives this machine a global presence. The heartbeat is
the socket itself (pings every 25 s), so `--watch` is no longer required
for online presence — the bridge IS the heartbeat.

From the desktop app: Log in → *Machines* → **"Make this the main
server"** → the same claim + bridge flow runs in-app, with a prompt to
install missing services (Part 4). Phones pair with `nexus node pair`
(on any logged-in machine) or an in-app button.

What the other machines of the SAME account see: single-active policy —
promoting a new node demotes the old one automatically. Other USERS are
never affected: every registry query is owner-filtered.

## Part 3 — Link a phone (or any device) with zero open ports

The owner (logged in anywhere) mints a pairing code; the device types
it once:

```bash
# owner side (any machine with the CLI logged in, or the desktop app)
nexus node pair
# → 6-digit code, valid 10 minutes, shown once
```

Device side (mobile/desktop app "Add this device"): enter the code →
the app receives a scoped device token (`capture,read,sync`) and opens
the relay attach WebSocket to the control plane. What happens on the
wire:

1. The device sends its ephemeral X25519 public key to the node
   (through the plane, sealed pipe).
2. The node replies with its own ephemeral key; both derive the session
   key. **The control plane saw only public keys.**
3. Every request/response afterwards is sealed
   (`HMAC-SHA256` authenticated encryption, per-frame nonce, replay
   window). The node unwraps and runs the request through its real API —
   ownership filters and scope checks included.

If the node is also reachable directly (LAN, Tailscale/Headscale
MagicDNS, Cloudflare Tunnel), clients may bypass the relay and use the
endpoint — the relay is the universal fallback that needs nothing.

| Method | Setup | Notes |
| --- | --- | --- |
| **Relay (built-in)** | pairing code only | zero open ports; works anywhere both sides have internet |
| Tailscale/Headscale | install on node + clients | p2p when possible, encrypted, free/self-hosted |
| Cloudflare Tunnel | `cloudflared tunnel --url http://localhost:8000` | public URL, rotates on restart |
| LAN | `http://<lan-ip>:8000` | at home |

## Part 4 — Install services in-app (STT, LLM)

When the node is promoted, the app checks what is installed and prompts
for the rest:

```bash
nexus services status          # {"stt": "faster-whisper"} etc.
nexus services install stt     # pip faster-whisper (base ~150 MB on first use)
nexus services install llm     # Ollama manual steps (native app)
```

The same endpoints drive the desktop app's prompts
(`GET /api/services/status`, `POST /api/services/install {service,
model}`): the UI asks "Install transcription? ~150 MB on first use" and
the node runs the install as its own user. Installs require the
`admin`/`devices` scope — a paired phone (capture-only) can never
install software.

## Operations cheat sheet

```bash
curl https://<cp>/health                          # mode: control-plane|node
nexus node resolve                                # active node (or null)
nexus node list                                   # all your nodes
nexus node claim --name "..."                     # rotate key + re-activate
nexus node pair                                   # mint a pairing code
nexus services status                             # STT/LLM present?
```

- **Node offline?** A connected bridge socket counts as fresh; if the
  machine sleeps, resolution returns null until it returns.
- **Deploy an update**: `git push` — Render auto-deploys; CI runs the
  test suite (63 tests) first.
- **Multi-worker scaling**: move rate-limit/lockout/relay tables to the
  shared store (interfaces are already isolated in `ratelimit.py`).

## What was verified (tests: 63/63 green)

- Control-plane isolation: personal-data endpoints 404 in control-plane
  mode (subprocess-level fresh-boot test).
- Lockout: 5 wrong passwords → 401 even with the right password; expiry
  restores login; identical error bodies for unknown/locked accounts.
- Throttling: 429 + Retry-After after the per-(IP, email) limit.
- Pairing: lifecycle (mint → redeem → consumed), 5-strike death,
  isolation across users, auth required to mint.
- Crypto: pure-Python X25519 cross-verified against the `cryptography`
  package on random keypairs (both directions + pubkey derivation).
- Relay e2e: ECDH handshake → sealed request → executed by the node's
  REAL FastAPI app (201 + task in DB) → sealed response; replay of the
  same nonce rejected; unauthenticated relayed request → 401 (the relay
  cannot bypass node auth); wrong api_key/unknown node refused at the
  socket handshake (4401).
- Services: status endpoint; install guarded by admin/devices scope
  (capture-only device token → 403); unknown service refused.
