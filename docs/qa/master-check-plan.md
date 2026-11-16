# NEXUS Master Check Plan — manual verification of every feature since the core service began

**Scope**: every feature commit from the 10th commit `3ea9525` (step 1 —
Node hardening, where core-service implementation began) through the
current tip `043561f`. 13 verification items, grouped by feature area,
ordered by dependency: local foundations first, then networked surfaces,
then the apps, then the newest GitHub/QoL features.

**Protocol (how we work)**:

1. You verify ONE item at a time, top to bottom, on a real machine
   (Windows or macOS — the two platforms we demo on). Each item lists
   exact commands and the exact expected result for each step.
2. Anything that deviates → file a report (template at the bottom):
   item id, step number, what you ran, what you saw, what you expected.
   One issue per report entry is ideal, but batch them per item.
3. I fix, commit (with the issue id in the message), and push; the fix
   gets a regression test where feasible. Then you re-verify just that
   step and we move to the next item.
4. Items must stay in order — later items depend on earlier ones (e.g.
   Item 7 needs the node from Item 1; Item 10 needs the OAuth app from
   Phase 0).

**Automated coverage already in place** (what your manual pass double-
checks against): 82 pytest (core), 24-check `scripts/demo_setup.py`,
17-check `scripts/e2e_github_cli.py`. Your reports are the ground truth
for what automation cannot see: real browsers, real phones, real cloud
dashboards, real install dialogs.

---

## Phase 0 — Set up the external services (once, before Item 1)

These are the third-party services the stack depends on. Do them all in
one sitting; they cost nothing on free tiers.

| # | Service | What it gives us | How to set up |
|---|---------|------------------|---------------|
| S1 | **GitHub account + OAuth app** | repo push/pull; the GitHub linking feature (Item 10) | You already have github.com/kn1ght073/nexus. Create ONE OAuth app at **github.com/settings/developers** → "New OAuth App": name `nexus-node`, homepage any valid URL (e.g. the repo URL), callback left blank or `http://127.0.0.1:8000/api/github/authorize/callback` (the desktop flow posts the code back itself, so the redirect just needs to be *somewhere*). Note the **Client ID**, generate a **Client Secret**. Scopes stay minimal: the app requests `read:user` only. |
| S2 | **Render account** (render.com, free tier) | hosts the control plane (auth + node registry + relay) | Sign up with the GitHub login. Render dashboard → New → **Blueprint** → select the `kn1ght073/nexus` repo → it reads `services/core-api/render.yaml` and provisions `nexus-control-plane` (free plan, health path `/health`). After first deploy, set in the dashboard: `NEXUS_DATABASE_URL` (from S3), `NEXUS_JWT_SECRET` (64-hex — `python -c "import secrets; print(secrets.token_hex(32))"`), `NEXUS_CORS_ORIGINS` (e.g. `["tauri://localhost","http://localhost:5173"]`). Expect the URL `https://nexus-control-plane.onrender.com`. |
| S3 | **Neon or Supabase Postgres** (pick ONE) | the control plane's database (free tier) | **Neon** (neon.tech): sign up → Create project → copy the *pooled* connection string into `NEXUS_DATABASE_URL`. **Supabase** (supabase.com): New project → Project Settings → Database → Connection string (URI, use the *pooler* port 6543 for Render's free single worker). Either works; Neon is serverless-friendly, Supabase gives you a dashboard to inspect rows. |
| S4 (optional) | **Ollama** (ollama.com/download) + `ollama pull llama3.2` | local LLM for the inbox intent pipeline (Item 6) | Install the native app for your OS, pull `llama3.2` (~2 GB). Skip if you don't want to test the AI item's LLM leg — STT alone can be verified with `faster-whisper`. |
| S5 (optional) | **Tailscale** (tailscale.com) | zero-config LAN alternative to the relay | Not required — the secure relay (Item 8) is the primary path and needs nothing installed. Only useful if you later want direct LAN speeds. |

**Phase 0 checklist**: S1 client id/secret noted → S3 URL pasted into S2 →
`curl https://nexus-control-plane.onrender.com/health` returns
`{"status":"ok","service":"nexus-core","mode":"control-plane"}` → (S4
optional) `ollama list` shows llama3.2.

**Fallback if you'd rather avoid Render entirely**: self-host the same
control plane with `cd services/core-api && cp .env.example .env && docker
compose up -d` (Postgres 16 + the API + optional Caddy TLS; see
`docker-compose.yml`). Everything else in this plan works identically
against it.

---

## Item 1 — Core auth, ownership isolation, path jail, CORS (`3ea9525`)

**Machine**: laptop/desktop, any OS. **Setup**: `nexus bootstrap --yes`
(creates `~/.nexus-venv`), then start the node:
`~/.nexus-venv/bin/python -m uvicorn nexus_core.main:app --port 8000`
(Windows: `~\.nexus-venv\Scripts\python.exe -m uvicorn ...`).

| Step | Command / action | Expected |
|------|------------------|----------|
| 1.1 | `nexus register` (email+password ≥8 chars) then `nexus login` | both succeed; token stored in `~/.nexus-cli.json` |
| 1.2 | `nexus whoami` | your email + id, no error |
| 1.3 | `nexus project create "Verification P1"`; `nexus task add "Task A" --project 1`; `nexus project list` | the project and task appear, owned by you |
| 1.4 | Register a SECOND user (edit `~/.nexus-cli.json` away or use `NEXUS_CLI_CONFIG=/tmp/u2.json` on a second shell): `nexus project list` as user 2 | user 2 sees **nothing** of user 1's projects/tasks/notes — ownership isolation |
| 1.5 | `nexus file roots` | lists the storage roots (e.g. `~/Documents`) |
| 1.6 | `nexus file browse` then attempt a `../` escape (e.g. search a path outside the root) | files under the root list fine; traversal outside the jail is refused |
| 1.7 | 5 wrong-password `nexus login` attempts, then a correct one | wrong ones fail identically; the 6th (correct) is *locked out* (401, Retry-After logic) — lockout works; wait 5 min or restart node to clear |
| 1.8 | visit `http://127.0.0.1:8000/docs` in a browser | **404** (docs hidden by default); with `NEXUS_EXPOSE_DOCS=true` env they appear |
| 1.9 | `curl -i http://127.0.0.1:8000/health` | headers include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` |

## Item 2 — Sync engine + scoped device tokens (`713f6ba`)

**Setup**: node running (Item 1). You + second user or second shell.

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | `nexus sync` (first, full pull) | panel with projects/tasks/notes counts + `Server time:` line |
| 2.2 | As user A create a task; then `nexus sync --since <server_time from 2.1>` | only the new task appears; older rows excluded |
| 2.3 | `nexus device token --device-id 1 --scopes read` | issues a scoped token bound to device 1 |
| 2.4 | Use that token: `curl -H "Authorization: Bearer <tok>" http://127.0.0.1:8000/api/tasks` | read works |
| 2.5 | Try a write with the read-scoped token (POST a task) | **403** — scope enforcement is real |
| 2.6 | Create a device with capability `capture` only (via `/api/devices`), mint a `capture` token, POST to `/api/inbox` | 202 accepted; the capture token can submit but cannot list tasks |

## Item 3 — CLI sync/`--json` surface polish (`0a03afd`)

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | `nexus task list --json`, `nexus sync --json` | valid JSON only on stdout (tables/panels go to stderr) — machine-parseable |
| 3.2 | `python -c "import json,sys; json.load(sys.stdin)" < <(nexus project list --json)` | parses cleanly |
| 3.3 | `nexus task today` | only today's due tasks |
| 3.4 | `nexus task done <id>` | task status flips to completed |

## Item 4 — Desktop app scaffold (Tauri 2) (`0ddd61d`)

**Prereqs**: Node 18+, Rust (`rustup`), platform extras (Windows: WebView2
+ MSVC; macOS: Xcode CLT).

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | `cd apps/desktop && npm install` | installs cleanly (takes minutes) |
| 4.2 | Core running (Item 1); `npm run dev` | Vite serves the frontend at localhost:5173; login form reachable |
| 4.3 | Log in with Item-1 credentials in the web view | dashboard/projects/tasks/devices views load real data from the node |
| 4.4 | `npm run build` (tsc + vite) | compiles without errors |
| 4.5 | `cd src-tauri && cargo build` (or `npm run tauri dev` if configured) | Rust shell builds; the window opens and loads the same views (GUI step — needs your desktop) |

## Item 5 — Mobile scaffold (Android/Compose) (`32d9703`)

**Prereqs**: Android Studio (or SDK + `gradle wrapper --gradle-version
8.9`), phone or emulator.

| Step | Action | Expected |
|------|--------|----------|
| 5.1 | Open `apps/mobile` in Android Studio; set `NEXUS_CORE_URL` in `app/build.gradle.kts` to your dev PC's LAN IP (or `adb reverse tcp:8000 tcp:8000` for loopback) | project syncs/gradle resolves (first build downloads deps) |
| 5.2 | `./gradlew :app:assembleDebug` | APK builds |
| 5.3 | Install on device/emulator, log in with Item-1 creds | login works over LAN/adb-reverse; quick-capture adds a task visible via `nexus task list` on the PC |
| 5.4 | Toggle a task done on the phone | reflects in `nexus task list` |

## Item 6 — Inbox AI pipeline skeleton (`617d3c5`)

| Step | Action | Expected |
|------|--------|----------|
| 6.1 | `nexus services status` | `{}` (or `{"stt": ...}` if faster-whisper installed) |
| 6.2 | `nexus services install stt` | install job streams progress; afterwards `services status` shows stt |
| 6.3 | POST to `/api/inbox` (text form) — e.g. `curl -X POST -H "Authorization: Bearer <tok>" -F "text=Remind me to water plants tomorrow" http://127.0.0.1:8000/api/inbox` | **202** with `inbox_item_id` (capture token works here) |
| 6.4 | Poll `/api/inbox/<id>` (GET) | item transitions pending → (LLM leg: intent extracted, or a structured "no LLM available" state if Ollama absent — not a crash) |
| 6.5 | With Ollama running (S4): submit "Add a task to buy milk tomorrow" | intent becomes a structured task suggestion (action engine output), not free text |

## Item 7 — Online access: control plane + node promotion (`f8c82c2`)

**Setup**: Phase 0 done (Render URL live).

| Step | Action | Expected |
|------|--------|----------|
| 7.1 | `curl https://<render-host>/health` | `"mode":"control-plane"` |
| 7.2 | `nexus cp set --url https://<render-host>`; `nexus cp login` (same email/password as node — accounts live on the CP) | login succeeds from anywhere |
| 7.3 | Visit any personal-data endpoint on the CP: `curl https://<host>/api/tasks -H "Auth..."` | **404** — personal routers are not mounted on the control plane |
| 7.4 | `nexus node claim --name "My Laptop" --platform macos` (no `--watch`) | node registered; `nexus node resolve` returns it |
| 7.5 | `nexus node list` | your node(s) with heartbeat freshness |
| 7.6 | `nexus login` against the NODE (loopback) again | local node auth unaffected by CP login |

## Item 8 — Zero-port secure relay (`bac38fb`)

| Step | Action | Expected |
|------|--------|----------|
| 8.1 | On the node: `nexus node claim --watch --bridge` (foreground heartbeats + relay bridge) | bridge connects outbound to the CP (no ports opened on the node) |
| 8.2 | `nexus node pair` | prints a short pairing code with TTL |
| 8.3 | On the phone app (Item 5 build, pointed at the CP URL) choose "link device" and type the code | pairing succeeds; the device attaches through the relay |
| 8.4 | From the phone (away from LAN, mobile data): create a task | task appears on the node (`nexus task list`) — E2E sealed frame executed by the node |
| 8.5 | Type the same pairing code twice / a wrong code 5 times | code consumed on first success; after 5 strikes the session dies (codes are single-purpose) |
| 8.6 | While the bridge is down (Ctrl-C), `nexus node resolve` | returns null (or falls back) — heartbeat timeout works |

## Item 9 — In-app bootstrap + services plan (`fb69629`)

| Step | Action | Expected |
|------|--------|----------|
| 9.1 | `curl "http://127.0.0.1:8000/api/services/packages" -H "Authorization: Bearer <tok>"` | JSON: stt/llm entries (docs links, sizes, prompts), environment (uv flag, requirements, commands), mirrors |
| 9.2 | `?mirror=tuna` on the same endpoint | plan commands carry the tuna index URL |
| 9.3 | `nexus services install bootstrap --mirror tuna` | runs the same engine as the CLI bootstrap |
| 9.4 | `nexus bootstrap --dry-run` | prints the plan only, executes nothing |

## Item 10 — GitHub linking + highlights (`e1d01ef` + `e629706`)

**Setup**: S1 OAuth app; node env vars `NEXUS_GITHUB_CLIENT_ID`,
`NEXUS_GITHUB_CLIENT_SECRET` (in the node's environment or `.env` next
to it).

| Step | Action | Expected |
|------|--------|----------|
| 10.1 | `nexus github status` | "No GitHub account linked" panel |
| 10.2 | `nexus github connect` | panel: **open github.com/login/device** + one-time code (browser may auto-open); the command polls |
| 10.3 | In the browser (any device, even your phone): enter the code, authorize as kn1ght073 | within seconds the CLI prints "GitHub account kn1ght073 linked (scopes: read:user)" |
| 10.4 | `nexus github status` | linked, your login, linked date — **no token anywhere in the output** |
| 10.5 | `nexus github highlights` | panel: name, repos/followers/following counts; repo table (name, stars, language, last push); activity lines ("pushed N commit(s) to …") |
| 10.6 | `nexus github highlights` again immediately | same content marked `(cached)` — 5-min cache; `--refresh` refetches |
| 10.7 | `nexus github highlights --json` | machine-readable JSON (login, profile, repos[], events[]) |
| 10.8 | `nexus github unlink` | unlinked + token revoked at GitHub (check github.com/settings/connections — the app disappears from authorized apps) |
| 10.9 | Desktop leg: with the node running, GET `/api/github/authorize-url` (browser or curl with token) → open the URL → authorize → the callback code+state flow links (if you test via the desktop app's UI when wired; otherwise verify the 403/400 behaviors below) | cross-user state is refused; replaying a used state returns 400 |
| 10.10 | `nexus github highlights` before any link | clear 409-style guidance panel, not a crash |

## Item 11 — Interactive install interview (`3f870c2`)

| Step | Action | Expected |
|------|--------|----------|
| 11.1 | Fresh machine/venv: `nexus bootstrap` (no --yes) | "NEXUS first-run setup" panel; asks "Install the full NEXUS stack now?" |
| 11.2 | Answer no | "Setup deferred" guidance panel, exit 0, nothing installed |
| 11.3 | Re-run, answer yes → "Is your PyPI link slow or unreliable?" → yes | mirrors list shown (tuna/aliyun/ustc/sjtu); type `tuna` |
| 11.4 | Continue | "What's happening" guidance (venv/uv/per-user), then the **plan** shows `index: https://pypi.tuna...`; confirm to run |
| 11.5 | Let it finish | "Setup complete" panel with the exact uvicorn start command for YOUR platform |
| 11.6 | Run that command | node boots from the managed venv (this was the bug we fixed — verify it really imports `nexus_core`) |
| 11.7 | `nexus bootstrap --yes` (CI mode) | no prompts, plan runs directly |

## Item 12 — Cross-platform demo script (`92f81ec`)

| Step | Action | Expected |
|------|--------|----------|
| 12.1 | `python scripts/demo_setup.py` from the repo root | 24 PASS lines, `24/24 checks passed`, exit 0; artifacts cleaned |
| 12.2 | `python scripts/demo_setup.py --keep` | same + `scripts/demo-venv/` and demo files kept for inspection |
| 12.3 | Run it twice in a row | both green — hermetic (no "email already registered" from run 1's DB) |

## Item 13 — Docs match reality (`34af7ac`, `043561f`)

| Step | Action | Expected |
|------|--------|----------|
| 13.1 | Read `docs/deploy/online-access.md` Part 5 while doing Item 10 | every documented command/endpoint matches what you actually ran |
| 13.2 | `.env.example` GitHub keys | names match `NEXUS_GITHUB_*` you used in Item 10 |
| 13.3 | `progress.md` step 9 | matches what you observed across Items 9–12 |

---

## Report template (paste per item)

```
ITEM: <n> (<name>)
ENV: <Windows 11 / macOS 15 …, real phone? browser?>
RESULT: PASS except steps below

ISSUE <item>.<step>:
  ran:        <exact command or UI action>
  expected:   <from the plan>
  observed:   <what actually happened — paste output/screenshot text>
  notes:      <anything odd but maybe not a bug>
```

Send one item's report at a time; I fix + commit + push, you re-verify the
failed steps only, then we advance. When all 13 report PASS, the check
phase is done and we resume new features (next queued: desktop first-run
UI wiring to `/api/services/packages` + bootstrap job polling, and the
GitHub "Connect" button hitting `/api/github/authorize-url`).

## Item dependency map

```
Phase 0 (S1–S3) ──┬─► 7 (control plane) ─► 8 (relay+pairing+phone)
                  └─► 10 (GitHub linking needs S1)
1 (node+auth) ─► 2 ─► 3 ─► 6 ─► 9 ─► 11 ─► 12
1 ─► 4 (desktop), 1 ─► 5 (mobile)     [4/5 independent of 2/3]
13 last, after everything it references
```
