# NEXUS Desktop (Tauri 2) — scaffold

The primary rich client for the NEXUS ecosystem (Major project): a Tauri 2
shell with a React + TypeScript frontend, talking REST + WebSocket to the
NEXUS Core API running on the Windows Node (or another LAN host).

> **Status**: source scaffold — login, dashboard, projects, tasks, devices,
> activity views wired to the real Core endpoints. Build locally; nothing is
> committed from `node_modules`/`target`.

## Prerequisites

- Node.js 18+ and npm
- Rust 1.77+ with cargo (`rustup`)
- Platform extras: Windows → WebView2 + MSVC; macOS → Xcode CLT

## Build & run (dev)

```bash
# 1. Start the Core (repo root):
cd ../../services/core-api
pip install -r requirements.txt
uvicorn nexus_core.main:app --reload        # http://127.0.0.1:8000

# 2. Register an account once (any interface):
cd ../../apps/cli && pip install -r requirements.txt
nexus register && nexus login

# 3. Run the desktop shell:
cd ../../apps/desktop
npm install
npm run tauri dev
```

Login inside the app with the same account. The app stores the JWT in
localStorage for now; the production plan moves it to the OS keychain
(vault/stronghold plugin) — see the architecture plan §6.3.

## Production build

```bash
npm run tauri build    # produces the platform installer (NSIS/MSI on Windows)
```

## Layout

```text
apps/desktop/
├── index.html               # vite entry
├── package.json             # react 18 + vite 6 + TS 5
├── src/
│   ├── api.ts               # Core API client (auth, projects, tasks, devices, activity)
│   ├── App.tsx              # shell: header + nav + view routing
│   ├── styles.css           # dark theme
│   └── views/
│       ├── LoginView.tsx    # login/register + Core health probe
│       └── DashboardView.tsx # dashboard/projects/tasks/devices/activity + live WS refresh
└── src-tauri/
    ├── tauri.conf.json      # window + CSP scoped to the Core's origins
    ├── Cargo.toml           # tauri 2 deps
    └── src/
        ├── lib.rs           # commands: core_base_url, core_health (Rust-side hooks)
        └── main.rs          # windows_subsystem attribute (no console window)
```

## Notes

- The WebSocket in `DashboardView` authenticates by sending the access token
  as the first frame (the Core's `/ws` contract, step 1).
- CSP (`tauri.conf.json`) only allows connections to `127.0.0.1:8000` (dev)
  and `nexus.local:8443` (LAN TLS deployment).
- Icons: `src-tauri/icons/` must be added before `tauri build` (`npx tauri
  icon <source.png>` generates the full set).
