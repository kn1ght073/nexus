# NEXUS Documentation — Errors, Contradictions & Proposed Fixes

Scope: the five uploaded documents (`NEXUS_Initiation_and_Project_Submission.md`, `NEXUS_Personal_Digital_Infrastructure_Project.md`, `NEXUS_CLI_Minor_Project.md`, `NEXUS_Desktop_Major_Project.md`, `NEXUS_Mobile_Minor_Project.md`) and the GitHub repository `kn1ght073/nexus` (commit `e4f05d4`). The five uploaded files are byte-identical to the copies in `repo/nexus/docs/`, so every finding applies to both sets.

Severity: **E** = error (objectively wrong), **C** = contradiction between files, **W** = warning / inconsistency worth fixing.

---

## A. Naming & Identity

**A1 (E). CLI binary name contradiction: `pcc` vs `nexus`.**
The Personal Digital Infrastructure (PDI) doc uses `pcc` as the CLI command 34 times (`pcc status`, `pcc automation list`, `pcc hash file.zip`, `pcc search`, …, sections 13, 14, 18, Phase 4, §37), while every other document — CLI proposal (`nexus status`…), Initiation plan (`nexus project create`…), the repo's `pyproject.toml` (`nexus = "main:app"`) and CLI README — uses `nexus`. The PDI doc never mentions `nexus` as a command at all.
*Fix:* replace all `pcc` commands with the `nexus` equivalents (matching the existing command surface: `pcc task add` → `nexus task add`, `pcc device send report.pdf mac` → `nexus file send report.pdf --device mac`). `pcc` looks like a leftover from an earlier project name ("Personal Command Center").

**A2 (E). Repository README is a one-liner, contradicting the Initiation plan.**
The Initiation doc (§4) prescribes `README.md` at the repo root introducing the monorepo; the actual README contains only the title `# NEXUS — Personal Digital Infrastructure`.
*Fix:* add a short overview: ecosystem diagram, the three projects, quick-start for `services/core-api` and `apps/cli`, pointer to `docs/`.

**A3 (C). "The repository contains only the CLI" vs the actual repo.**
The task brief says the repo holds only the CLI, but it also contains a working `services/core-api` FastAPI backend (auth/devices/projects/tasks/notes + file browse/search endpoints, SQLite, 9 commits, mock auth) and full `docs/`. This changes the architecture starting point: the Core already exists in skeleton form.
*Fix:* update the project context to "CLI + core-api MVP implemented; desktop and mobile not started". The architecture plan in the companion file builds on this fact.

---

## B. Diagram & Structural Errors

**B1 (E). Initiation §3 diagram demotes the Windows Node to a peer of the clients.**
The "Recommended Initial Architecture" diagram shows `NEXUS CORE` feeding three children: `NEXUS WINDOWS NODE`, `NEXUS CLI`, `NEXUS MOBILE` — placing the Windows Node *below* the Core as a sibling of clients, and omitting the Desktop as a client of the Core. But per every other section (Initiation §2, §5; PDI §4.1, §5; Desktop proposal "Architecture") the Windows Node **is** the host of the Core (API/database/storage/AI), not something the Core calls into. The same diagram's "NEXUS DESKTOP MAJOR" box sits *above* the Core, implying the Desktop calls the Core directly — fine — but then the Node-as-sibling is impossible.
*Fix:* restructure to the layering used in the companion architecture plan: CLIENT LAYER (Desktop, CLI, Mobile) → NEXUS CORE (hosted on) → WINDOWS NODE (DB, storage, AI, workers). The PDI §4.1 diagram already gets this right; make Initiation §3 match it.

**B2 (C). Entity list mismatch between the two main documents.**
Initiation §6 lists 10 entities (no Folder, Bookmark, Command, Notification, Download); PDI §3.3 lists 15 (adds Folder, Bookmark, Command, Notification, Download). The repo's `models.py` implements only 5 (User, Device, Project, Task, Note).
*Fix:* declare PDI §3.3 the canonical superset, mark Folder/Bookmark/Command/Notification/Download as post-MVP, and state the MVP subset (the repo's 5 + File metadata) explicitly in the Initiation doc.

**B3 (C). Desktop "Architecture" diagram in the Desktop proposal is inverted relative to the text.**
It shows `Desktop Client ↓ NEXUS Core API ↓ Database + Storage + Sync + Event Bus ↓ Windows NEXUS Node ↓ AI / Media / Downloads / Automation`, i.e. the Windows Node sits *below* the database and the AI/media services hang off the Node. The text and PDI §4.1 say the Core *runs on* the Node and the AI/media/download services are subsystems the Core orchestrates.
*Fix:* collapse to: Desktop Client → NEXUS Core (on Windows Node) → {DB, Storage, Workers(AI/Media/Downloads/Automation)}.

**B4 (W). The eight product components differ in name across documents.**
Initiation §18: "Intelligence Layer"; PDI §6: "Personal AI Layer" (also "NEXUS AI" in §41). Initiation §18 "Storage & Download Center" vs PDI §6 "Download / Transfer Manager". Same subsystems, drifting labels.
*Fix:* pick one canonical name per component (suggest the PDI §41 names, which the final hierarchy uses) and use it everywhere.

**B5 (W). Minor-project numbering contradiction.**
Initiation §1: "Minor Project 1 = CLI, Minor Project 2 = Mobile". PDI §15: "MINOR PROJECT 1 = Android, MINOR PROJECT 2 = CLI" (and its §17/§18 headers agree). File names ("Mobile_Minor", "CLI_Minor") don't resolve it.
*Fix:* standardize on the Initiation order (CLI = Minor 1, Mobile = Minor 2) or vice versa, and correct the PDI §15 block.

---

## C. Contradictions With the Repository

**C1 (E). CLI `task list` reads a field that does not exist: `is_completed`.**
`apps/cli/main.py` `task list` renders `t.get("is_completed")`, but the API's `Task` schema exposes `status` ("pending"/"in_progress"/"completed") — there is no `is_completed` field anywhere in `schemas.py` or `models.py`. Consequence: **the table's Status column always shows "⏳ Pending"** (`.get()` returns None), including completed tasks. (The Textual TUI in `tui.py` handles this correctly via `format_status(t.get("status"))` — only the non-interactive command is affected.) The CLI also never uses the `PATCH /tasks/{id}/status` endpoint that exists for this purpose.
*Fix:* `status_icon = "✅ Done" if t.get("status") == "completed" else "⏳ Pending"`, and add a `nexus task done <id>` command calling the PATCH endpoint.

**C2 (E). CLI sends `Bearer mock-token-123`, which the server never validates — but also never issues.**
`main.py`/`tui.py` `get_headers()` hardcode `Authorization: Bearer mock-token-123`. The API's `get_current_user` ignores the header entirely (returns first/auto-creates user), and `/auth/login` returns `mock_token_for_{id}`. So the token in the CLI matches nothing the server issues: harmless today, broken the day real auth lands.
*Fix (docs + code):* document that auth is mocked for the MVP (the `windows-node-mvp.md` plan already flags this), store the login token in the CLI config, and send it; then implement real JWT validation server-side (see D2).

**C3 (E). Committed binary database file `services/core-api/nexus.db.bak`.**
`git ls-files` confirms `nexus.db.bak` (64 KB SQLite) is tracked, despite `.gitignore` listing `*.db` (the `.bak` extension evades the pattern). The file may contain test user/projects rows; committing databases is exactly what the Initiation plan's clean-monorepo intent rules out.
*Fix:* `git rm --cached services/core-api/nexus.db.bak`, add `*.db*` / `nexus.db*` to `.gitignore`, keep data files out of version control.

**C4 (E). GET /tasks and GET /notes ignore ownership.**
`api.py` queries `db.query(models.Task).all()` and `db.query(models.Note).all()` with the comment "For MVP, get all tasks" — while projects/devices are correctly filtered by `owner_id`. Any second user would see everyone's tasks/notes. Also `Task`/`Note` models have no `owner_id`, only `project_id`, so the filter must go through the project join.
*Fix:* filter via `Task.project.owner_id == current_user.id` (join) or add an `owner_id` column; until multi-user exists, state the single-user assumption in the docs instead of implying per-user isolation.

**C5 (E). Unjailled filesystem endpoints.**
`/files/browse` defaults to `Path.home()` and accepts any `path` parameter; `/files/search` walks the entire tree under `path` (skipping hidden dirs) and reads every text file ≤1 MB, returning matched lines. No allowlist, no symlink resolution check, no traversal guard — and CORS is `*`. Combined, any LAN device can read arbitrary home-directory file content through the API. This contradicts the security architecture both main docs demand (device authorization, explicit permissions, "do not expose the Windows node carelessly").
*Fix:* introduce configurable storage roots (`settings.storage_roots`), resolve real paths and reject anything outside them, cap search depth/results, and require the `filesystem.read` scope.

**C6 (E). CORS `allow_origins=["*"]` with `allow_credentials=True`.**
`main.py` sets both; per the CORS spec this combination is invalid — browsers reject credentialed requests when the origin is the wildcard. It also contradicts the local-network trust model (a malicious webpage on your LAN could hit the API from a browser).
*Fix:* `allow_origins=["tauri://localhost", "http://localhost:5173"]` (dev) and no wildcard in production; or drop credentials and use token headers.

**C7 (W). Binding: `main.py` runs Uvicorn on `127.0.0.1`, but the ecosystem requires LAN access.**
The `cli-assignment.md` plan itself documents running `--host 0.0.0.0` for cross-device use; the code as committed is loopback-only, so Mac/Android can never connect. Not a bug for dev, but a doc-vs-code gap to call out.
*Fix:* make host/port configurable (env `NEXUS_HOST`/`NEXUS_PORT`), default loopback for dev, LAN bind + Windows Firewall private-profile rule documented for deployment.

**C8 (W). README examples leak a real username.**
`apps/cli/README.md` examples use `/Users/jaishastri/...` — the developer's actual macOS username — in a public repository.
*Fix:* replace with generic paths (`/Users/yourname/Documents` or `~/Documents`).

**C9 (W). `requirements.txt` omits the Textual dependency that `tui.py` imports.**
`pyproject.toml` lists `textual` (unpinned) but `requirements.txt` (used by the documented `pip install -r` flow) does not, so `nexus ui` fails with ImportError in a fresh env. Also `textual` unpinned while everything else is pinned.
*Fix:* add `textual==<compatible version>` to `requirements.txt`.

**C10 (W). Repo structure vs the Initiation plan's prescribed layout.**
The plan prescribes `packages/`, `infrastructure/`, `services/sync|ai|media|automation/`; the repo has only `apps/cli` and `services/core-api`. Fine at this stage, but the docs describe folders that don't exist yet without marking them "planned".
*Fix:* mark them "planned/post-MVP" in the docs, or add README placeholders in the repo.

---

## D. Internal Document Issues

**D1 (E). "No conflicts identified" in the task brief is itself wrong.**
The supplied brief's Conflict Resolution section says none were found; this file lists 10 outright errors/contradictions (A1–A3, B1–B3, C1–C7).
*Fix:* acknowledge the conflicts catalogued here.

**D2 (C). Security requirements vs the "no real auth" MVP.**
Both main docs require authenticated users, device-level authorization, encrypted transport (PDI §32; Initiation Phase 1 "User/device authentication"), yet the implemented MVP has mock auth, plaintext HTTP, and a wildcard CORS. The docs never reconcile "mock for now" with their own security architecture.
*Fix:* add an explicit security roadmap to the Initiation doc: MVP (mock, loopback) → V1 (JWT + device tokens, TLS on LAN) → V2 (per-device scopes, signed commands). The companion architecture plan §6 does this.

**D3 (C). macOS role contradiction.**
Initiation §2/§5 treat Windows as *the* Node and other machines as clients; PDI Phase 2 deliverable says "Windows desktop client" AND "macOS desktop client" (fine), but PDI §12 (Component 6) and use cases describe the Mac as both client and transfer destination with desktop-class capabilities ("read/write project data, transfer files, execute approved device actions" §33) — i.e. a peer node — without ever defining a Mac Node role. The task brief adds: only the Windows desktop app will be submitted, but the design must support macOS.
*Fix:* define one sentence of doctrine: "Windows is the authoritative Node; macOS is a first-class client with device capabilities, and can be promoted to a Node by configuration." (Applied in the architecture plan §7.)

**D4 (W). Database recommendation drift.**
PDI §27 recommends SQLite first, PostgreSQL later; the repo chose SQLite (good); but the Desktop proposal says "relational data model" without naming anything, and no doc mentions the vector store needed for the semantic-search feature they emphasize. SQLite FTS5 / sqlite-vec are never mentioned.
*Fix:* extend the stack section: SQLite + FTS5 for text search, sqlite-vec or LanceDB for embeddings, PostgreSQL+pgvector only if multi-Node.

**D5 (W). Sync mechanism promised everywhere, specified nowhere.**
Desktop proposal ("synchronization"), CLI proposal (`nexus sync`), PDI §31 (metadata/file/event split) — but no document defines the actual protocol (pull/push, revisions, conflict resolution, tombstones), and the repo has no `/sync` endpoints or `updated_at` columns.
*Fix:* the architecture plan §3 specifies it (revision-based pull/push, LWW+tombstones, chunked file sync); mirror that into the Initiation doc.

**D6 (W). Phase numbering is inconsistent between the two planning documents.**
Initiation uses Phase 0–13 with Universal Inbox at Phase 6; PDI uses Phase 0–12 with Universal Inbox at Phase 7 and AI at Phase 6 — the same milestones sit at different numbers, and the content order differs (Initiation: AI at Phase 8; PDI: AI at Phase 6, before Inbox).
*Fix:* adopt one canonical phase list (recommend PDI's: prove core → clients → ecosystem → AI → inbox → media → downloads → automation → memory), and align the Initiation doc's section numbering to it.

**D7 (W). MVP scope contradiction.**
Initiation §25 MVP = Node + DB + API + Auth + Projects/Tasks/Notes/Files + Desktop (no Android, no CLI). PDI §35 MVP = Core + Desktop + **Android + CLI** + Inbox + AI search. Two different "MVPs".
*Fix:* define MVP (the Initiation one, matching the assignment slice already built) and call the PDI version "V1".

**D8 (W). Example workflow attribution error.**
The task brief says "user records a note in the Nexus mobile app; the Windows server automatically transcribes it and adds it to the user's list" — matching the docs' flows. But the CLI proposal's Example Workflow claims "Android can display/notify it" for a *CLI-created* task, while the Mobile proposal only promises notifications for server/client events pushed to registered devices; neither defines that a CLI-created task notifies Android. Minor, but the docs imply a notification fan-out they never specify.
*Fix:* specify the event→notification rule in the Initiation doc: TASK_CREATED events fan out to all online registered devices with the `notifications` capability.

---

## E. Code-Level Nits (repo)

**E9 (W). Dead config field.** `CLIConfig.token` exists and is saved, but nothing ever writes or sends it — related to C2.
**E10 (W). `datetime.utcnow` is deprecated** in Python 3.12 (repo targets modern Python); use `datetime.now(timezone.utc)`.
**E11 (W). Broad `except Exception: pass`** in `/files/search` swallows server errors silently — return a 500 or log it.
**E12 (W). `GET /notes` response model `Note` lacks `owner` scoping fields**, so the API cannot express per-user notes even in the schema (ties to C4).
**E13 (W). `search` result cap is 50 but no pagination parameters** exist on any list endpoint — the sync engine will need `?since=` cursors anyway.
**E14 (W). No tests exist**, despite `windows-node-mvp.md` planning "simple pytest integration". Add at least endpoint smoke tests (health, create project, ownership filter).

---

## Priority Fix Order

1. **Security-critical**: C5, C6, C2, C4 (file jail, CORS, real auth, ownership filters) — before any LAN deployment.
2. **Correctness bugs users will see**: C1 (`is_completed`), C3 (committed db), C9 (missing dep), E10.
3. **Doc contradictions that mislead development**: A1 (`pcc`), B1 (Node-as-peer diagram), B5 (minor numbering), D6/D7 (phase & MVP drift).
4. **Hygiene**: A2, C7, C8, C10, D4, D5, D8, E9, E11–E14.
