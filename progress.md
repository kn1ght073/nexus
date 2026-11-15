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

- **Phase**: Step 6 (AI layer skeleton) — in progress
- **Last commit**: `33d1ce7` (step 5)
- **Tests**: `cd services/core-api && python -m pytest tests/ -q` → 34 passed
- **Loop health**: each session = one roadmap step, committed & pushed, ledger updated

## Roadmap (from the architecture plan §8)

| # | Step | Status | Notes |
|---|------|--------|-------|
| 1 | Harden the Node: real auth, ownership-filtered queries, path-jailed files, CORS lockdown, remove nexus.db.bak | ✅ done | `nexus_core/` package; Argon2+JWT; 28 tests; CLI updated to real auth; repo hygiene |
| 2 | Extend the Core: `updated_at/revision/deleted_at` + `/sync/pull` `/sync/push`; WebSocket event channel; device registry with capabilities + scopes | ✅ done | commit `a4e2c02`; revision bumped on all 9 mutation handlers; push LWW + stale-conflict results; device tokens with capability-validated scopes; 34/34 tests |
| 3 | Extend the CLI in place: `devices`, `sync`, `task today`, `--json`, config token store; keep Typer structure and TUI | ✅ done | commit `b3f1ed0`; `nexus sync`, `--json` on all 8 listing commands (stdout JSON, stderr rich), `nexus device token`; e2e 8/8 parse OK; keyring store deferred (documented) |
| 4 | Desktop Tauri shell: login/pairing, dashboard, projects/tasks/notes, file manager, live events | ✅ done (scaffold) | commit `096ecd4`; Tauri 2 + React/TS: login/register, dashboard, tasks/devices/activity views, live WS refresh, CSP scoped to Core origins; keychain token store + file manager = next milestone; no build toolchain in sandbox |
| 4b | Desktop fallback (sandbox-scope): produce design doc + static HTML prototype of the dashboard/login (self-contained, inline CSS/JS) | ✅ merged into 4c | the React app IS the prototype; extra static HTML would duplicate — skipped deliberately |
| 4c | Desktop fallback: Tauri 2 scaffold — `apps/desktop` with tauri.conf.json, Rust src-tauri skeleton, React+TS frontend skeleton, README on building locally | ✅ done | as above |
| 5 | Mobile: pairing, capture, tasks, upload, notifications; Room cache + background sync | ✅ done (scaffold) | commit `33d1ce7`; Compose login + quick-capture tasks + done, Retrofit client, EncryptedSharedPreferences tokens, loopback/LAN network policy; Room cache + voice capture = next milestone |
| 6 | AI layer: faster-whisper + Ollama + embeddings behind validation/action engine; Universal Inbox pipeline | 🔄 in progress | interfaces + worker skeleton + mock pipeline; models can't be downloaded in sandbox |
| 7 | Media/downloads/automation | ⬜ pending | per Initiation doc build order; only after core ecosystem works |

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

**Next session → Step 6.** AI layer skeleton per plan §2.1/§6.5: a
`services/core-api/nexus_core/workers/` package with (a) `stt.py` —
faster-whisper transcription interface with a mock fallback when the model is
absent, (b) `llm.py` — Ollama client + strict JSON-Schema intent validation,
(c) `action_engine.py` — validates structured intents against a permission
registry before executing (create-task only in the skeleton), (d) an inbox
job queue on the existing event bus, wired as FastAPI background tasks. Tests
with the mock pipeline (no model downloads in sandbox). One step, commit,
push, update this ledger, stop.
