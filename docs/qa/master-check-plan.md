# NEXUS Master Check Plan — Verification of Core Architecture, Modernized CLI, and Live Infrastructure

**Scope**: Comprehensive manual and automated verification covering core node hardening, owner isolation, path jail, sync engine, scoped tokens, desktop/mobile interfaces, live control-plane promotion (`https://nexus-control-plane-uvi8.onrender.com`), edge relay routing, GitHub device flow, and modern CLI v0.2.0 diagnostic capabilities.

**Automated verification baseline**:
- 106 automated tests in `services/core-api/tests/` (API security, token scopes, client console, GitHub flow, online access)
- 24 automated unit tests in `apps/cli/tests/` (CLI v0.2.0 modular architecture, client pooling, OS keyring, doctor diagnostic engine)
- 17-step end-to-end device flow check in `scripts/e2e_github_cli.py`
- 24-step complete stack orchestration check in `scripts/demo_setup.py`

---

## Phase 0 — Production Infrastructure & External Services

| # | Service | Production State | Configuration & Endpoints |
|---|---------|------------------|---------------------------|
| S1 | **GitHub OAuth App** | Registered | Client ID & Secret configured for device flow (`nexus-node`) |
| S2 | **Render Live Control Plane** | **LIVE (Active)** | `https://nexus-control-plane-uvi8.onrender.com`<br>Health probe: `curl -s https://nexus-control-plane-uvi8.onrender.com/health` returns `{"status":"ok","service":"nexus-core","mode":"control-plane"}` |
| S3 | **Neon PostgreSQL Database** | **LIVE (Active)** | Cloud-hosted Postgres instance bound to Render control plane via `NEXUS_DATABASE_URL` |
| S4 | **Local LLM / STT** *(Optional)* | Optional local AI | Ollama (`llama3.2` on `http://127.0.0.1:11434`) + `faster-whisper` |

---

## Item 0 — CLI Diagnostics & Health Suite (`nexus doctor`)

**Machine**: macOS / Linux / Windows developer workstation.

| Step | Command / action | Expected Output |
|------|------------------|-----------------|
| 0.1 | `nexus --version` | `nexus version 0.2.0` |
| 0.2 | `nexus doctor` | Formatted diagnostic table displaying: Runtime (`PASS`), Python version, Credential Store (`Keyring` or file fallback), Config file (`mode: 0o600`), and live Control Plane connectivity. |
| 0.3 | `nexus doctor --json` | Valid machine-readable JSON containing `{"status": "...", "checks": [...]}`. |
| 0.4 | `nexus status` | `Connected to nexus-core` with authenticated account identity. |

---

## Item 1 — Core Auth, Ownership Isolation, Path Jail & Security Headers

| Step | Command / action | Expected Output |
|------|------------------|-----------------|
| 1.1 | `nexus register --email operator@example.com --password Password123!` then `nexus login --email operator@example.com --password Password123!` | Registration successful (persisted in Neon DB); login succeeds; session token stored securely in OS Keyring. |
| 1.2 | `nexus whoami` | Displays User ID, email (`operator@example.com`), role (`user`), and API endpoint. |
| 1.3 | `nexus project create "Sovereign Project A"`; `nexus task add "Audit Syscall Stubs" --project 1`; `nexus project list` | Project and task created and displayed in formatted table. |
| 1.4 | Register a second user in isolated config (`NEXUS_CLI_CONFIG=/tmp/nexus_u2.json nexus register --email operator2@example.com --password Password123!`); run `nexus project list` | Second user sees empty project list (complete tenant ownership isolation). |
| 1.5 | `nexus files roots` (or `nexus file roots`) | Lists active sandboxed storage boundaries (e.g. `~/Documents`). |
| 1.6 | Attempt directory traversal via `nexus files search` or browse outside root (`../`) | Access blocked; path traversal outside jail strictly refused. |
| 1.7 | Perform 5 incorrect login attempts, then 1 valid login | Account locked out via rate-limiting/brute-force defense (HTTP 401 with lockout delay). |
| 1.8 | Visit `https://nexus-control-plane-uvi8.onrender.com/docs` or `http://127.0.0.1:8000/docs` in browser | HTTP 404 by default (API documentation hidden unless `NEXUS_EXPOSE_DOCS=true`). |
| 1.9 | `curl -I https://nexus-control-plane-uvi8.onrender.com/health` | Security headers present: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`. |

---

## Item 2 — Incremental Sync Engine & Scoped Device Tokens

| Step | Command / action | Expected Output |
|------|------------------|-----------------|
| 2.1 | `nexus sync pull` | Summary panel with entities count and server timestamp cursor. |
| 2.2 | Create new task; execute `nexus sync pull --since <timestamp>` | Only the newly created entity delta is returned. |
| 2.3 | `nexus devices token --platform android --expires 15` | Issues a single-use onboarding pairing token with 15-minute expiration. |
| 2.4 | Mint read-scoped token via API; issue `curl -H "Authorization: Bearer <token>" .../api/tasks` | Read succeeds. |
| 2.5 | Attempt entity creation with read-scoped token | HTTP 403 Forbidden (granular scope enforcement). |

---

## Item 3 — Strict Unix Discipline & Output Streams

| Step | Command / action | Expected Output |
|------|------------------|-----------------|
| 3.1 | `nexus tasks list --json` | Pure JSON payload on stdout; zero styling or progress bars on stdout. |
| 3.2 | Pipe test: `nexus projects list --json \| python -m json.tool` | Successfully parses JSON without formatting corruption. |
| 3.3 | `nexus tasks today` | Returns only tasks with active daily deadlines. |
| 3.4 | `nexus tasks done 1` | Task status flips to `completed`. |

---

## Item 4 — Desktop Application (Tauri 2 + Vite)

| Step | Command / action | Expected Output |
|------|------------------|-----------------|
| 4.1 | `cd apps/desktop && npm install` | Clean dependency installation. |
| 4.2 | `npm run dev` | Local Vite dev server starts at `http://localhost:5173`. |
| 4.3 | Open desktop app; authenticate | App connects to default `https://nexus-control-plane-uvi8.onrender.com` or local node; entities load. |
| 4.4 | `npm run build` | TypeScript + Vite production compilation succeeds with zero errors. |
| 4.5 | `npm run tauri dev` (or `cargo build` in `src-tauri`) | Native Tauri window opens with working UI. |

---

## Item 5 — Mobile Client (Android Compose)

| Step | Command / action | Expected Output |
|------|------------------|-----------------|
| 5.1 | Inspect `apps/mobile/app/build.gradle.kts` | Default `NEXUS_CORE_URL` points to `https://nexus-control-plane-uvi8.onrender.com`. |
| 5.2 | Build debug APK: `./gradlew :app:assembleDebug` | Gradle compilation succeeds; APK generated in `build/outputs/apk/debug/`. |
| 5.3 | Launch mobile app; authenticate | Login connects to live control plane; captured inbox items synchronize. |

---

## Item 6 — Optional AI Services (Speech-to-Text & Local LLM)

| Step | Command / action | Expected Output |
|------|------------------|-----------------|
| 6.1 | `nexus services status` | Displays detection state of `stt` (`faster-whisper`) and `llm` (`ollama`). |
| 6.2 | `nexus services install stt` | Automated install of `faster-whisper`. |
| 6.3 | Submit text inbox item via API | HTTP 202 Accepted with assigned `inbox_item_id`. |
| 6.4 | Poll item status: `/api/inbox/<id>` | Intent parsing completes or gracefully flags offline LLM state without server crash. |

---

## Item 7 — Live Cloud Control Plane & Node Promotion

| Step | Command / action | Expected Output |
|------|------------------|-----------------|
| 7.1 | `curl https://nexus-control-plane-uvi8.onrender.com/health` | `{"status":"ok","service":"nexus-core","mode":"control-plane"}` |
| 7.2 | `nexus cp set https://nexus-control-plane-uvi8.onrender.com` | Control plane URL saved in configuration. |
| 7.3 | Verify tenant data isolation on control plane: `curl https://nexus-control-plane-uvi8.onrender.com/api/tasks` | HTTP 404 (Personal data routers remain local to edge nodes; never stored in cloud control plane). |
| 7.4 | `nexus nodes claim --name "Workstation-Primary"` | Host claimed as authoritative node; API key saved in Keyring. |
| 7.5 | `nexus nodes list` | Returns node registry table with live heartbeat timestamps. |
| 7.6 | `nexus nodes resolve` | Resolves currently active primary edge node. |

---

## Item 8 — Outbound Relay Bridge & Remote Edge Pairing

| Step | Command / action | Expected Output |
|------|------------------|-----------------|
| 8.1 | Run edge node with bridge: `nexus nodes claim --watch --bridge` | Outbound secure relay connection established to Render control plane. |
| 8.2 | `nexus nodes pair` | Generates single-use 6-digit numeric pairing code. |
| 8.3 | Submit pairing code from external client | Pairing acknowledged; client bridges through outbound relay without open inbound ports. |
| 8.4 | Submit task from remote mobile/web client | Task processed E2E on the local edge node. |

---

## Item 9 — GitHub Identity Linking & Highlights (OAuth Device Flow)

| Step | Command / action | Expected Output |
|------|------------------|-----------------|
| 9.1 | `nexus github status` | Displays linking status or prompts `Run 'nexus github connect'`. |
| 9.2 | `nexus github connect` | Outputs one-time user verification code and opens `github.com/login/device`. |
| 9.3 | Authorize in browser | Polling loop completes; displays `GitHub account <username> linked`. |
| 9.4 | `nexus github status` | Displays GitHub username, ID, and minimal granted scopes (`read:user`). Token remains unexposed. |
| 9.5 | `nexus github highlights` | Formatted summary of public repositories, stars count, and commit stream. |
| 9.6 | `nexus github highlights --json` | Emits structured JSON representation of developer activity. |
| 9.7 | `nexus github unlink` | Link removed and remote OAuth token revoked server-side. |

---

## Item 10 — Automated Regression Validation

Run the automated test matrix to ensure 100% test passing rate:

```bash
# 1. Modular CLI Test Suite (24 tests)
PYTHONPATH=apps/cli services/core-api/.venv/bin/pytest apps/cli/tests/

# 2. GitHub CLI E2E Verification (17 checks)
services/core-api/.venv/bin/python scripts/e2e_github_cli.py

# 3. Stack Bootstrap & Demo Verification (24 checks)
services/core-api/.venv/bin/python scripts/demo_setup.py

# 4. Core API Test Suite (106 tests)
services/core-api/.venv/bin/pytest services/core-api/tests/
```

---

## Verification Report Template

```
ITEM: <number> (<name>)
ENVIRONMENT: <macOS / Linux / Windows, python version>
STATUS: PASS / FAIL

OBSERVATIONS:
  step:       <step number>
  command:    <executed command>
  output:     <pasted terminal output>
  expected:   <matching expectation or discrepancy>
```
