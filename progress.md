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

- **Phase**: Step 3 (Extend the CLI) — in progress
- **Last commit**: `a4e2c02` (step 2)
- **Tests**: `cd services/core-api && python -m pytest tests/ -q` → 34 passed (as of step 2)
- **Loop health**: each session = one roadmap step, committed & pushed, ledger updated

## Roadmap (from the architecture plan §8)

| # | Step | Status | Notes |
|---|------|--------|-------|
| 1 | Harden the Node: real auth, ownership-filtered queries, path-jailed files, CORS lockdown, remove nexus.db.bak | ✅ done | `nexus_core/` package; Argon2+JWT; 28 tests; CLI updated to real auth; repo hygiene |
| 2 | Extend the Core: `updated_at/revision/deleted_at` + `/sync/pull` `/sync/push`; WebSocket event channel; device registry with capabilities + scopes | ✅ done | commit `a4e2c02`; revision bumped on all 9 mutation handlers; push LWW + stale-conflict results; device tokens with capability-validated scopes; 34/34 tests |
| 3 | Extend the CLI in place: `devices`, `sync`, `task today`, `--json`, config token store; keep Typer structure and TUI | 🔄 in progress | `devices` & `task today` exist from step 1; remaining: `nexus sync`, `--json` global flag |
| 4 | Desktop Tauri shell: login/pairing, dashboard, projects/tasks/notes, file manager, live events | ⬜ pending | outside sandbox scope — build the static prototype pages instead, document |
| 4b | Desktop fallback (sandbox-scope): produce design doc + static HTML prototype of the dashboard/login (self-contained, inline CSS/JS) | ⬜ pending | satisfies plan §2.2 for the review milestone |
| 4c | Desktop fallback: Tauri 2 scaffold — `apps/desktop` with tauri.conf.json, Rust src-tauri skeleton, React+TS frontend skeleton, README on building locally | ⬜ pending | real code users can run locally; no cross-compile in sandbox |
| 5 | Mobile: pairing, capture, tasks, upload, notifications; Room cache + background sync | ⬜ pending | Kotlin project scaffold + design doc; no emulator in sandbox |
| 6 | AI layer: faster-whisper + Ollama + embeddings behind validation/action engine; Universal Inbox pipeline | ⬜ pending | interfaces + worker skeleton + mock pipeline; models can't be downloaded in sandbox |
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

**Next session → Step 3.** Add `nexus sync` (pull to table output, `--json`
optional), a global `--json` flag on the CLI for machine-readable output of
task/project/note/device lists, and a `nexus device token` passthrough if
cheap. Keep Typer structure; do not touch the TUI beyond what --json needs.
One step, commit, push, update this ledger, stop.
