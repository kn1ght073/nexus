# NEXUS CLI (Command Line Interface)

NEXUS CLI is a professional, high-performance developer tool and edge node controller for the NEXUS sovereign infrastructure ecosystem.

## Key Architecture & Features

- **Modular Command Hierarchy**: Clean, domain-focused command groups (`auth`, `account`, `devices`, `nodes`, `projects`, `tasks`, `notes`, `files`, `sync`, `github`, `services`, `config`, `doctor`).
- **OS Keyring Integration**: Secure token storage backed by system keychains (macOS Keychain, Linux SecretService, Windows Credential Manager) with graceful fallback to `chmod 0600` file storage.
- **Deep Diagnostics Engine (`nexus doctor`)**: Instant verification of runtime, security backends, config file integrity, core node latency, control plane connectivity, and optional local services (STT, LLM).
- **Strict Unix Output Discipline**: Structured data to stdout, interactive progress spinners to stderr, full `--json` support across commands, and automatic `NO_COLOR` / non-TTY detection.
- **100% Backward Compatibility**: Preserves all root legacy commands and aliases (`login`, `register`, `logout`, `whoami`, `init`, `status`, `ui`, `search`, `bootstrap`, `cp`).

---

## Installation

### Direct from GitHub (Recommended)

Install the CLI directly without PyPI registration:

```bash
# Standard user/environment install
pip install git+https://github.com/kn1ght073/nexus.git

# Or isolated application install via pipx (recommended for global command use)
pipx install git+https://github.com/kn1ght073/nexus.git

# Or via uv
uv tool install git+https://github.com/kn1ght073/nexus.git
```

### Local Development / Editable Mode

```bash
uv pip install -e apps/cli
# Or:
pip install -e apps/cli
```

Verify your installation:

```bash
nexus --version
nexus doctor
```

### Interactive Cockpit TUI

Launch without arguments to enter the full-screen interactive cockpit:

```bash
nexus
```

---

## Command Reference

### Diagnostics & System Health

#### `nexus doctor`
Run full diagnostic probes across runtime, credentials, node connectivity, and services.
```bash
nexus doctor
nexus doctor --json
```

#### `nexus status`
Check live connection and authentication status with the configured NEXUS core node.
```bash
nexus status
```

---

### Authentication & Account Identity

> **Policy Notice**: Account creation and login are strictly governed by Google OAuth. Traditional password registration and login endpoints are disabled across the infrastructure.

#### `nexus auth login`
Authenticate using Google OAuth and store session tokens securely in the OS Keyring.
```bash
# Interactive Google OAuth browser flow:
nexus auth login

# Or supply pre-authenticated token:
nexus auth login --token <SESSION_TOKEN>
```

#### `nexus auth whoami`
Display identity, role, and permissions of the current session.
```bash
nexus auth whoami
nexus auth whoami --json
```

#### `nexus auth logout`
Revoke active session tokens server-side and purge local keychain credentials.
```bash
nexus auth logout
```

#### `nexus account overview`
Inspect sovereign account details, Google OAuth identity linking, and registered entity metrics.
```bash
nexus account overview
nexus account overview --json
```

#### `nexus account data`
Inspect entity tallies (projects, tasks, notes) and verify the zero-cloud sovereign retention policy.
```bash
nexus account data
nexus account data --json
```

#### `nexus account activity`
View the audit activity event stream with filtering.
```bash
nexus account activity --category auth --limit 10
```

---

### Devices & Hardware Nodes

#### `nexus devices list`
List all registered hardware devices, platform types, and online states.
```bash
nexus devices list
nexus devices list --json
```

#### `nexus devices inspect <device-id>`
Inspect hardware metadata, network properties, and capabilities for a specific device.
```bash
nexus devices inspect 1
```

#### `nexus devices token`
Generate a single-use onboarding token for new clients (mobile apps, laptops).
```bash
nexus devices token --platform android --expires 15
```

#### `nexus devices revoke <device-id>`
Revoke a device's authorization and unlink it permanently.
```bash
nexus devices revoke 2 --yes
```

#### `nexus nodes claim`
Claim this host machine as an authoritative NEXUS edge node.
```bash
nexus nodes claim --name "Workstation-Node" --watch
```

#### `nexus nodes list`
List all claimed edge nodes and their live heartbeats.
```bash
nexus nodes list
```

#### `nexus nodes resolve`
Query which node is currently elected as active primary node.
```bash
nexus nodes resolve
```

#### `nexus nodes pair`
Mint a temporary 6-digit numeric pairing code for edge onboarding.
```bash
nexus nodes pair
```

---

### GitHub Integration

#### `nexus github connect`
Link your GitHub account using the OAuth Device Flow (works headless & over SSH).
```bash
nexus github connect
```

#### `nexus github status`
Check GitHub account linking status and active scopes.
```bash
nexus github status
nexus github status --json
```

#### `nexus github highlights`
Display profile highlights, top repositories, and recent commit activity.
```bash
nexus github highlights
nexus github highlights --refresh
nexus github highlights --json
```

#### `nexus github unlink`
Unlink GitHub account and revoke tokens server-side.
```bash
nexus github unlink
```

---

### File Operations & Jailed Search

#### `nexus files list [path]`
Browse files inside the server's configured storage roots.
```bash
nexus files list
nexus files list ~/Documents
```

#### `nexus files roots`
List configured storage roots defining path jail boundaries.
```bash
nexus files roots
```

#### `nexus files search <query>` (or `nexus search <query>`)
Search for text inside files contained within the storage roots.
```bash
nexus files search "API_KEY"
```

---

### Projects, Tasks & Notes

#### `nexus projects list`
```bash
nexus projects list
nexus projects list --json
```

#### `nexus projects create <title> [--desc <desc>]`
```bash
nexus projects create "Project Apollo" --desc "Core architecture"
```

#### `nexus tasks list` / `nexus tasks today`
```bash
nexus tasks list
nexus tasks today
```

#### `nexus tasks add <title> [--project <id>]`
```bash
nexus tasks add "Refactor syscall stubs" --project 1
```

#### `nexus tasks done <task-id>`
```bash
nexus tasks done 5
```

#### `nexus notes list` / `nexus notes add <title> <content>`
```bash
nexus notes list
nexus notes add "Kernel Architecture" "Detailed notes on IRP handling..."
```

---

### Node Services (STT, LLM)

#### `nexus services status`
Show which optional services (faster-whisper, ollama) are installed or active.
```bash
nexus services status
```

#### `nexus services install <stt|llm|bootstrap>`
Install an optional service locally:
```bash
nexus services install stt
```

---

### Configuration Management

#### `nexus config list`
List active CLI parameters with automatic credential masking.
```bash
nexus config list
nexus config list --json
```

#### `nexus config get <key>` / `nexus config set <key> <value>`
```bash
nexus config get api_url
nexus config set api_url http://127.0.0.1:8000
```

#### `nexus config reset`
Clear all configuration and purge stored credentials from OS Keyring.
```bash
nexus config reset --yes
```

---

## Interactive TUI Control Center

Launching `nexus` in an interactive terminal automatically opens the full-screen NEXUS Terminal User Interface (TUI), combining the usability of GitHub CLI with the design aesthetics of Charmbracelet tools:

```bash
nexus
```

To explicitly launch the TUI or bypass it:

```bash
# Explicit launch
nexus ui

# Bypass TUI in interactive terminals (standard CLI help)
nexus --no-ui
```

### TUI Cockpit Architecture & Workspace Views

The NEXUS TUI is a desktop-grade personal infrastructure cockpit running inside the terminal, built on Textual and organized into four coordinated zones:

1. **Status Header**: Displays real-time telemetry, active CLI version, authenticated identity (Google OAuth), connected Core API / Control Plane URL, active profile, local node binding, and live rolling latency (min/max/avg). Supports privacy email masking.
2. **Navigation Sidebar**: Collapsible tree organized across two dedicated hierarchies:
   - **Workspace Views**: Direct access to all 12 operational cockpit sections.
   - **Command Explorer**: Canonical command categories with badge counters and filtered search.
3. **Interactive Workspace (Central Stage)**: Switchable multi-view container hosting:
   - **📊 Overview Dashboard (Default)**: ServerHub-inspired monitoring dashboard with account card, node & control plane card, fleet status, sync overview, CPU/RAM/Disk gauges, recent activity stream, and quick-action toolbar.
   - **👤 Account & Identity**: Sovereign identity profile, Google OAuth link state, GitHub integration, active sessions, and privacy email masking toggle.
   - **📱 Device Management**: Interactive hardware fleet table, search filter, device inspection card, pairing workflow, and revocation with safety confirmations.
   - **🖥️ Edge Nodes**: Claimed edge compute and storage nodes, heartbeat telemetry, liveness checks, and 8-character claim code redemption.
   - **🌐 Network & Relay**: Mesh topology monitor, active encrypted WebSocket tunnels, E2EE X25519 ECDH + ChaCha20-Poly1305 protocol status, and live ASCII topology diagram.
   - **🔄 Synchronization**: Engine health, delta tracking across projects, tasks, and notes, per-device sync table, zero-conflict invariants, and manual sync pull.
   - **📁 Files & Storage**: Super File inspired dual-pane browser with breadcrumbs, directory tree, live plaintext/config file preview pane, deep search, and jailed root path safety.
   - **📋 Notes & Tasks**: Sticky-note Kanban productivity board with 3-column task execution (Pending, In Progress, Completed), Sticky Notes Wall, and Project progress tracking.
   - **⚙️ Local Services**: Local machine and edge compute manager for STT (faster-whisper), LLM Runtime (Ollama), Bootstrap virtualenv, and Node Bridge daemon.
   - **🩺 Diagnostics Doctor**: Automated diagnostics engine with PASS/WARN/FAIL indicators, detailed failure cause explanations, remediation commands, and redacted report export.
   - **🛡️ Activity & Security**: Immutable sovereign audit event timeline with category/action filters, redacted payload inspection, and audit export.
   - **🛠️ Settings & Profiles**: Theme customization (Dark, Synthwave, Light), compact mode toggle, email privacy masking, startup view preferences, and profile switching.
   - **⚡ Command Explorer**: Unified discovery table with live filtering, argument requirements, and safety levels.
4. **Context Panel**: Selected resource information, command descriptions, parameter syntax, destructive confirmation warnings, and contextual execution triggers.

### Global Command Palette (`Ctrl+K` or `/`)

Press `/` or `Ctrl+K` from any screen to open the global Command Palette. Supports fuzzy search across all command names, token paths, descriptions, and categories.

### Keyboard Shortcuts Reference

| Key | Action |
| :--- | :--- |
| `1` - `9`, `0` | Quick Jump between Cockpit Workspace Views (1: Overview, 2: Account, 3: Devices, 4: Nodes, 5: Network, 6: Sync, 7: Files, 8: Tasks/Notes, 9: Doctor, 0: Activity) |
| `/` or `Ctrl+K` | Open Global Command Palette & Fuzzy Search |
| `?` | Toggle Keyboard Shortcuts Help Sheet |
| `r` | Refresh Status Header & Active View Telemetry |
| `p` | Open Profile Switcher & Settings Dialog |
| `w` | Launch Guided Setup Wizard |
| `q` | Quit Application |
| `Tab` / `Shift+Tab` | Cycle focus between Sidebar, Workspace, and Context Panel |
| `Up` / `Down` | Navigate lists and table rows |
| `Enter` | Activate / Execute selected item or command |
| `Esc` | Close modal dialog or clear active search filter |

---

### Profile Management

Manage multiple isolated server targets, environments, and credential sets:

```bash
# List all configured profiles
nexus config profile list

# Create a new profile pointing to a custom node or staging environment
nexus config profile create staging --url https://staging.nexus.local

# Switch active profile
nexus config profile switch staging

# Delete a profile and purge its scoped credentials
nexus config profile delete staging --yes
```

---

### Interactive TUI

#### `nexus ui`
Launch the full-screen interactive Terminal User Interface (TUI).
```bash
nexus ui
```
