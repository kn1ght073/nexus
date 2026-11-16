# NEXUS — Build Progress Ledger

> **Purpose**: durable state for the autonomous build loop. If a chat session
> loses context, read this file (and `git log --oneline -20`) to resume work.
> The plan of record is
> [`docs/architecture/NEXUS_Optimized_Architecture_Plan.md`](docs/architecture/NEXUS_Optimized_Architecture_Plan.md)
> (§8 Implementation Roadmap). Known errors and their statuses live in
> [`docs/architecture/NEXUS_Errors_and_Fixes.md`](docs/architecture/NEXUS_Errors_and_Fixes.md).

## How to use this file (for the agent)

1. Read **"Current state"**, **"Next step"**, and the last entry in the log.
2. Do the next step only. Do not add features beyond what the step lists.
3. When a step is complete: run its tests, update the log below (append, never
   rewrite history), commit with the prefix `feat(core)/`, `feat(cli)/`,
   `fix(core)/`, `docs:/`, `chore:` + step id, and push.
4. If blocked, record why in the step's log entry and move to the next
   unblocked plan step — do not stall the loop.
5. When all steps in "Roadmap" are ✅, mark the basic build **complete**,
   notify via the ledger, and stop scheduling further work.

## Current state

- **Phase**: Step 8 (online access: control plane + node promotion) — in progress
- **Last commit**: (see `git log -1`)
- **Tests**: `cd services/core-api && python -m pytest tests/ -q` → 45 passed
- **Loop health**: basic build (1–6) done; step 8 requested by the user: log in from anywhere, node becomes main server

## Roadmap (from the architecture plan §8)

| # | Step | Status | Notes |
|---|------|------|--------|-------|
| 1 | Harden the Node: real auth, ownership-filtered queries, path-jailed files, CORS lockdown, remove nexus.db.bak | ✅ done | `nexus_core/` package; Argon2+JWT; 28 tests; CLI updated to real auth; repo hygiene |
| 2 | Extend the Core: `updated_at/revision/deleted_at` + `/sync/pull` `/sync/push`; WebSocket event channel; device registry with capabilities + scopes | ✅ done | commit `a4e2c02`; revision bumped on all 9 mutation handlers; push LWW + stale-conflict results; device tokens with capability-validated scopes; 34/34 tests |
| 3 | Extend the CLI in place: `devices`, `sync`, `task today`, `--json`, config token store; keep Typer structure and TUI | ✅ done | commit `b3f1ed0`; `nexus sync`, `--json` on all 8/8 parse OK; keyring store deferred (documented) |
| 4 | Desktop Tauri shell: login/pairing, dashboard, projects/tasks/notes, file manager, live events | ✅ done (scaffold) | commit `096ecd4`; Tauri 2 + React/TS: login/register, dashboard, tasks/devices/activity views, live WS refresh, CSP scoped to Core origins; keychain token store + file manager = next milestone; no build toolchain in sandbox |
| 4b | Desktop fallback (sandbox-scope): produce design doc + static HTML prototype of the dashboard/login (self-contained, inline CSS/JS) | ✅ merged into 4c | the React app IS the prototype; extra static HTML would duplicate — skipped deliberately |
| 4c | Desktop fallback: Tauri 2 scaffold — `apps/desktop` with tauri.conf.json, Rust src-tauri skeleton, React+TS frontend skeleton, README on building locally | ✅ done | as above |
| 5 | Mobile: pairing, capture, tasks, upload, notifications; Room cache + background sync | ✅ done (scaffold) | commit `33d1ce7`; Compose login + quick-capture tasks + done, Retrofit client, EncryptedSharedPreferences tokens, loopback/LAN network policy; Room cache + voice capture = next milestone |
| 6 | AI layer: faster-whisper + Ollama + embeddings behind validation/action engine; Universal Inbox pipeline | ✅ done (skeleton) | commit `d077cac`; mock + Ollama backends, strict intent schema, permission-checked action engine, /inbox text+audio with 202 background pipeline; 40/40 tests |
| 7 | Media/downloads/automation | ⬜ deferred | plan says: only after core ecosystem works; needs real backends (download clients, media servers) — next phase, after LAN TLS + Room cache land |
| 8 | Online access: hosted control plane (auth+node registry, no personal data) + node promotion + deploy guide | 🔄 in progress | control-plane mode, Node model + /api/nodes, CLI cp/node/services, Dockerfile+render.yaml+CI, docs/deploy/online-access.md; 45/45 tests |

## Step log (append-only)

### Step 1 — Harden the Node ✅ (commit: `feat(core): step 1 — real auth, ownership, file jail, CORS lockdown`)

Rebuilt `services/core-api` as the `nexus_core/` package (FastAPI + Uvicorn +
SQLAlchemy + SQLite WAL):

- Real auth: Argon2id hashing, JWT access/refresh, persisted signing secret;
  `mock-token-123` auto-created-user flow removed (errors file C2/D2).
- Ownership: every Task/Note row carries `owner_id`; all list/get/patch/delete
  queries ownership-filtered (C4); two-user isolation covered by tests.
- File jail: `/files/browse` + `/files/search` resolve paths and require
  membership in `NEXUS_STORAGE_ROOTS`; traversal/symlink escapes → 403; depth
  and result caps (C5).
- CORS locked to explicit origins (tauri://localhost + vite dev) instead of
  `allow_origins=["*"]` with credentials (C6).
- Activity log (`Activity` model + `/api/activity`) records every mutation
  per user; WebSocket `/ws` pushes domain events (auth by first-frame token).
- SQLite: WAL + `PRAGMA foreign_keys=ON` per connection; UTC-aware `utcnow`
  (E10); tombstones `deleted_at` for soft deletes.
- CLI: `register/login/logout/whoami`, `task done`, `task today`, `devices`,
  `file roots`, `note list`; fixed `is_completed` rendering bug (C1), search
  command name, missing `textual` pin (C9), username leak in README (C8).
- Hygiene: `nexus.db.bak` removed & untracked (C3), `.gitignore` hardened,
  root README rewritten (A2), core-api README added.
- Verification: 28/28 pytest (auth flows, isolation, jail, WS, sync pull),
  live uvicorn smoke (health/register/login/CRUD/jail/WS), CLI e2e vs live
  server — all green. Deliverables exported to `/home/z/my-project/download/`.

**Next session → Step 2.** ~~Add `revision` integer columns + `bump_revision()`
on mutation for Task/Note/Project; add `POST /api/sync/push` accepting client
changes with revision + last-writer-wins and returning the server revision per
row; tests for push conflicts (stale revision → 409 or server-wins detail).
Do not linger: one step, commit, push, update this ledger, stop.~~

### Step 2 — Extend the Core ✅ (commit: `a4e2c02`)

- `revision` integer column on Project/Task/Note (default 1, indexed);
  `bump_revision()` called in all 9 mutation handlers (create/update/status/
  done/tombstone) across projects/tasks/notes routers.
- `POST /api/sync/push`: accepts creates (id=None), updates and deletes
  (deleted=true → tombstone). Last-writer-wins: writes with
  `revision >= server_revision` are applied; stale writers get
  `accepted=false, conflict=true, server_revision=<current>` so clients can
  rebase. Cross-user ids → "not found" (isolation tested).
- Device tokens: `POST /api/devices/{id}/token` validates requested scopes
  against the device's declared capabilities (undeclared scope → 400),
  issues a JWT bound to the device id with the granted scope list.
  `require_scope()` dependency: interactive tokens (scope="user") pass
  everything; device tokens must intersect the route's allowed set —
  files need read/filesystem, sync/pull needs read/sync, sync/push needs
  sync/automation/filesystem, device-token issuance needs admin/devices.
- Tests: 34/34 (6 new) + live uvicorn smoke (push create; read-scoped token
  pulls 200, pushes 403).

**Next session → Step 3.** ~~Add `nexus sync` (pull to table output, `--json`
optional), a global `--json` flag on the CLI for machine-readable output of
task/project/note/device lists, and a `nexus device token` passthrough if
cheap. Keep Typer structure; do not touch the TUI beyond what --json needs.
One step, commit, push, update this ledger, stop.~~

### Step 3 — Extend the CLI ✅ (commit: `b3f1ed0`)

- `nexus sync [--since ISO]`: pulls `/api/sync/pull`, renders a summary panel
  + per-task change lines, or full JSON with `--json`.
- `--json` flag on all 8 listing commands (task list/today, project list,
  note list, devices, file list, search, sync): raw JSON on stdout, rich
  tables redirected to stderr — `nexus task list --json | jq ...` works.
  Implementation: per-command `json_output: bool = _json_flag()` parameter +
  `_set_json_mode()` + `output_json()` early return before table rendering.
- `nexus device token <id> [--scopes read,capture]`: issues capability-scoped
  device tokens (400-handling for undeclared scopes).
- Keyring-backed token store deferred (would add a dependency; `~/.nexus-cli.json`
  stays for now, documented in the ledger as deliberate).
- Verified by live e2e: 8/8 `--json` commands emit parseable JSON; plain table
  mode unchanged; register/login/CRUD all green.

**Next session → Step 4c.** ~~Scaffold `apps/desktop` as a Tauri 2 project:
`tauri.conf.json`, `src-tauri/` Rust skeleton (main.rs with nexus core URL
config), React+TS frontend skeleton (login view + dashboard shell + API client
module hitting the Core's REST endpoints), and a README with local build
instructions. Do not attempt to build (no Rust/npm toolchain in the sandbox);
commit source only. One step, commit, push, update this ledger, stop.~~

### Step 4c — Desktop Tauri scaffold ✅ (commit: `096ecd4`)

- `apps/desktop/src-tauri/`: tauri.conf.json (1200×800 window, CSP allowing
  only 127.0.0.1:8000 + nexus.local:8443 REST/WS), Cargo.toml (tauri 2),
  build.rs, lib.rs (`core_base_url`, `core_health` commands as the Rust-side
  hooks for tray/service integration), main.rs (windows_subsystem).
- Frontend (vite 6 + react 18 + TS strict): `api.ts` client (login/register,
  projects, tasks + done, devices, activity, health), `LoginView` (login /
  register + live Core status), `DashboardView` (dashboard, projects, tasks
  with add/complete, devices, activity feed; WebSocket `/ws` first-frame
  token auth triggers refresh on any event), dark theme styles.
- README: prerequisites, dev flow (Core → CLI register → `npm run tauri
  dev`), production build, layout notes (icons via `npx tauri icon`).
- Verified: all JSON configs parse, all relative imports resolve, file tree
  complete. Source-only (no npm/Rust in sandbox) — builds locally.

### Step 5 — Mobile scaffold ✅ (commit: `33d1ce7`)

- `apps/mobile/`: Gradle version catalog (AGP 8.5.2, Kotlin 2.0.20, Compose
  BOM 2024.09, Retrofit 2.11 + Moshi, OkHttp 4.12, Room 2.6.1,
  security-crypto, datastore).
- `NexusApi.kt`: Retrofit interface + DTOs for auth (login/register/me),
  tasks (list/create/done), notes, devices — matching the Core's schemas
  including `revision`.
- `TokenStore.kt`: JWTs in EncryptedSharedPreferences (Keystore-backed
  AES256), core URL in plain DataStore.
- `ui/ViewModels.kt`: LoginViewModel + TasksViewModel + Compose screens —
  login form (8+ char password hint) and quick-capture task list with Done.
- `network_security_config.xml`: cleartext only for 127.0.0.1/localhost
  (adb reverse dev flow); commented nexus.local CA-pinning block for LAN TLS
  pairing; base-config denies cleartext.
- README: dev build steps, LAN pairing, next milestones (Room offline cache +
  /sync, voice capture → STT job, foreground-service WS notifications).
- Source-only (no Android SDK in sandbox) — builds in Android Studio.

**Next session → Step 6.** ~~AI layer skeleton per plan §2.1/§6.5: a
`services/core-api/nexus_core/workers/` package with (a) `stt.py` —
faster-whisper transcription interface with a mock fallback when the model is
absent, (b) `llm.py` — Ollama client + strict JSON-Schema intent validation,
(c) `action_engine.py` — validates structured intents against a permission
registry before executing (create-task only in the skeleton), (d) an inbox
job queue on the existing event bus, wired as FastAPI background tasks. Tests
with the mock pipeline (no model downloads in sandbox). One step, commit,
push, update this ledger, stop.~~

### Step 6 — AI layer skeleton ✅ (commit: `d077cac`)

- `workers/stt.py`: faster-whisper when installed; deterministic mock
  (sha256-derived pseudo-transcript) otherwise — pipeline testable without
  model weights.
- `workers/llm.py`: `INTENT_SCHEMA` (action ∈ create_task|create_note, title
  1–200 chars, optional description/priority, `additionalProperties: false`);
  `validate_intent` rejects bad shapes, unknown fields, prose-wrapped JSON;
  `extract_intent_via_ollama` (localhost:11434) + `extract_intent_mock`;
  `extract_intent(backend="auto")` tries Ollama then falls back.
- `workers/action_engine.py`: the only executor. `PERMISSIONS` maps actions
  to token scopes; execute_intent checks the actor's scope, then creates the
  row with bump_revision + activity + events, exactly like the REST routers.
- `routers/inbox.py`: `POST /api/inbox` (text form) and `POST
  /api/inbox/audio` (multipart blob → `{storage_root}/inbox/`), both 202 +
  background `run_pipeline`; `GET /api/inbox/{id}` status (result JSON
  decoded). Pipeline statuses: pending → processing → completed |
  rejected | failed (with error captured).
- `InboxItem` model (kind, content, transcript, backend, result, error,
  status, owner_id, timestamps).
- Tests: 40/40 — text pipeline → task created + `[ai:text]` activity; audio
  mock-STT pipeline; cross-user isolation (404); device token without
  capture scope → 403; 8 intent-validation unit cases; action-engine scope
  enforcement (capture OK, read rejected).

---

## Completion summary — basic build finished

The roadmap's basic scope (steps 1–6) is **complete** as of commit `d077cac`
(2026-11-15). What exists:

- **Core API** (`services/core-api/nexus_core/`): real auth (Argon2+JWT),
  ownership-isolated CRUD for projects/tasks/notes, path-jailed file
  browse/search, activity timeline, sync engine (revisions + pull/push LWW),
  scoped device tokens, WebSocket events, Universal Inbox with a
  permission-checked AI pipeline (mock backends until Ollama/Whisper are
  installed locally). **40/40 tests.**
- **CLI** (`apps/cli/`): full command surface incl. login/register/logout,
  sync, `--json` pipeline output, device tokens; TUI preserved.
- **Desktop** (`apps/desktop/`): Tauri 2 + React/TS scaffold with
  login/dashboard/tasks/devices/activity views and live WS updates.
- **Mobile** (`apps/mobile/`): Kotlin/Compose scaffold with login +
  quick-capture tasks, encrypted token store, LAN TLS network policy.

**Deliberately not done** (recorded so the next session does not re-derive):
step 7 (media/downloads/automation) per the plan's build order; LAN TLS +
mDNS discovery; Room offline cache; keychain token stores; real AI backends
(needs local model downloads); keyring CLI store. These are the next
milestones — pick them up one at a time with the same step discipline.

**Loop note**: the Z.ai scheduled-task tool was unavailable in this sandbox
(cron tool errored "No such tool available" twice). The loop ran as a single
continuous session instead: one roadmap step per iteration, each committed
and pushed (bb718a3 → a4e2c02 → b3f1ed0 → 096ecd4 → 33d1ce7 → d077cac),
ledger updated after each. All state is durable in this file + git history,
so any future session can resume from `git log` + this file even without the
scheduler.

### Step 8 — Online access: control plane + node promotion 🔄→✅ (this session)

User request: "log in from anywhere,3 .8/45/45 tests" — implemented as:

- **Control-plane mode** (`NEXUS_CONTROL_PLANE_MODE=true`): create_app mounts
  only auth/devices/activity/nodes; personal-data routers (tasks/projects/notes
  files/inbox/sync) are NOT mounted — enforced by a test that fails if any
  of those endpoints respond non-404.
- **Node registry** (models.py Node + routers/nodes.py): claim (single-active
  policy, api_key rotation on re-claim, computed is_online from heartbeat
  age), heartbeat (revives stale nodes), /nodes/active (null when offline),
  services reporting, delete. Isolation tested (user B sees []).
- **Deployment**: NEXUS_DATABASE_URL (Postgres via psycopg2-binary,
  postgres:// → postgresql:// normalization, pool_pre_ping/ping + recycle
  300s), NEXUS_JWT_SECRET (env-precedence over file), control_plane_mode,
  node_heartbeat_timeout=90s. Dockerfile (python:3.12-slim, uvicorn 0.0.0.0),
  render.yaml (blueprint, free plan, healthcheck /health, envVars with
  sync:false for secrets), .github/workflows/ci.yml (pytest on push/PR).
- **CLI**: config.py(.control_plane_url/.node_id/.node_api_key.
- **CLI commands**: cp set/login (login against control plane, works
  anywhere), node claim --watch (30s heartbeat, foreground), resolve
  (active node or null, --json), list (table), services status (local
  detection: faster-whisper import probe, Ollama port probe), services
  install stt|llm (pip install faster-whisper; Ollama manual instructions;
  reports detected services to control plane). e2e green: cp set → cp login
  → claim → list → resolve --json (pure JSON on stdout) → services status;
  /api/tasks on control plane → 404.
- **Docs**: docs/deploy/online-access.md (architecture diagram, data policy
  table, Render+Neon/Supabase step-by-step, Tailscale/Cloudflare/ngrok
  endpoint options, free-tier caveats, CLI README section (command table).
- **Tests**: 45/45 green (5 new: claim/demote/re-claim, heartbeat + stale
  resolution + revival, services reporting + isolation, control-plane
  subprocess test, DATABASE_URL normalization).

**Next session →** step 8 is code-complete; remaining: the user follows
docs/deploy/online-access.md to deploy (needs their Render/Neon accounts);
step 7 (media/downloads/automation) stays deferred per plan build order.

### Step 8b — Any-device promotion + secure relay + public-internet hardening ✅ (this session)

User request: "any device can act as the main server; the app securely
links the phone to the CLI on any OS without opening ports; global and
public; render the API private with proper authorization so no one can
access another user's data; in-app prompts to install STT/LLM" —
implemented as (priorities per the user's four):

1. **User security / authorization**: every relay/pairing/devices query
   owner-filtered; pairing codes bind devices to the code OWNER only;
   relayed requests run through the node's real FastAPI stack (device
   token scopes enforced on-node); locked/unknown accounts answer
   identically (no probing); Argon2 timing equalizer on unknown emails.
2. **Control-plane hardening** (routers/auth.py + ratelimit.py + main.py):
   sliding-window login/register throttle per (IP,email) with
   Retry-After; account lockout 5×5min (bounded, expiring); /docs +
   /openapi.json hidden unless NEXUS_EXPOSE_DOCS=true; OWASP security
   headers on every response; 10 MB body cap (413); /health minimal
   (status+mode only, no version).
3. **Any-device main server + zero-port relay**: models
   PairingSession/RelayLink; routers/relay.py (owner mints 6-digit code,
   10-min TTL, salted-HMAC stored, single-use; device attach WS; node
   outbound WS keyed by node api_key; plane pipes sealed bytes both
   ways); nexus_core/pairing.py (pure-Python X25519 RFC 7748 —
   cross-verified against `cryptography` in tests — + HMAC-SHA256
   frame sealing with per-frame nonces and replay windows);
   nexus_core/node_bridge.py (node half: ECDH handshake, unwrap,
   execute via the node's own ASGI app, seal response, ping
   super-heartbeat 25 s, reconnect with backoff). CLI: node pair, claim
   now writes nexus_node.json + offers foreground bridge.
4. **In-app installs**: routers/services.py (GET /api/services/status,
   POST /api/services/install {service,model} as background job,
   GET /api/services/install/{id}; install requires admin/devices
   scope — a capture-only paired phone gets 403).
- **Self-hosted option** (user recommendation, open source over free
  tiers): services/core-api/docker-compose.yml (control plane +
  postgres:16 + caddy:2 TLS), .env.example, Caddyfile; docs add Option B
  + Headscale as direct-link alternative.
- **Tests**: 63/63 green (18 new in tests/test_online_access.py:
  lockout+expiry, throttle+Retry-After, hidden docs/headers/body cap,
  pairing lifecycle/5-strike/isolation/auth-to-mint, X25519 vs lib,
  seal tamper/base64-crash rejection, relay e2e incl. replay + 401
  through relay + socket 4401s, attach socket pipe both directions,
  services scope enforcement).
- **Docs**: online-access.md rewritten (new architecture diagram, data
  policy + relay rows, security-posture table, self-hosted Option B,
  Parts 2-4 rewritten for any-device claim + pair + in-app installs);
  README gains an "Online access" quick section.

**Next session →** step 7 (media/downloads/automation) stays deferred
per plan build order; desktop app UI wiring for Machines/pairing/
install prompts; optional account export/import between tiers; LAN TLS.

### Step 8c — In-app setup (bootstrap) + guide QoL pass ✅ (this session)

User request: "commit to GitHub; update online-access.md after part 3 so
all pip installations, uv, and other setup steps are performed inside
the app, with appropriate links" — implemented as:

- **nexus_core/bootstrap.py**: the self-setup engine. plan_bootstrap()
  computes the exact commands WITHOUT running (inspectable plan; --dry-run
  shows it): per-user venv (~/.nexus-venv), uv auto-detected and probed
  (`uv --version` must succeed), plain `python -m venv` + pip fallback
  with pip self-upgrade; all core+CLI pins as the default requirement
  list; named PyPI mirrors (tuna/aliyun/ustc/sjtu + default) or raw
  https URLs, validated (garbage rejected); run_bootstrap() executes
  with live echo, failure tail, and a bounded timeout (900 s);
  write_uv_config() persists the mirror for future uv runs.
- **API**: GET /api/services/packages — machine-readable setup plan for
  first-run screens (services with labels/sizes/docs links, environment:
  uv_available/venv/python/index/requirements/commands, mirrors list,
  docs links incl. uv/pip/python.org); POST /api/services/install
  accepts service "bootstrap" (model field = mirror name, validated).
  Schema pattern extended ^(stt|llm|bootstrap)$.
- **CLI**: new `nexus bootstrap [--mirror] [--dry-run] [--venv-dir]`
  command (plan panel, live progress, final "how to start the node"
  panel); `nexus services install bootstrap [--mirror]` runs the same
  engine. Verified live in the sandbox: uv detected, tuna mirror flowed
  into the install command, dry-run printed only the plan.
- **Docs**: online-access.md Part 2 rewritten (bootstrap first, manual
  steps framed as "what it automates"), Part 4 renamed "Everything
  installs from inside the app" — one-time environment setup section
  with uv/pip/mirror links, services table with sizes+links
  (faster-whisper, ollama), "Where Python itself comes from" with
  python.org + uv install one-liners for Windows/macOS/Linux; operations
  cheat sheet gains bootstrap; verified-tests list updated (68/68).
  download/online-access.md synced from the repo copy.
- **Tests**: 68/68 green — 5 new (bootstrap plan shapes incl. pip
  upgrade/venv create/mirror propagation, uv detection + fallback,
  packages endpoint auth/links/mirror-propagation/400-on-garbage,
  bootstrap install service accepted + mirror validation with the
  installer stubbed so tests never spawn subprocesses or write real
  venvs — hermetic via tmp_path venv dirs after catching a real
  ~/.nexus-venv leak from the un-stubbed first version).
- **Push**: sandbox has no git remote and no gh CLI — commits made
  locally (nexus repo + outer my-project repo); push commands left for
  the user (git remote add + push).

**Next session →** desktop app first-run UI wiring to
GET /api/services/packages + POST bootstrap job polling; step 7
(media/downloads/automation) still deferred per plan build order.
