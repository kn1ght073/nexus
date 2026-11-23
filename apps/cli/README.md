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

Install in editable mode using `uv` (recommended) or `pip`:

```bash
uv pip install -e apps/cli
```

Verify your installation:

```bash
nexus --version
nexus doctor
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

#### `nexus auth login`
Log in to NEXUS Core and store session tokens securely in the OS Keyring.
```bash
nexus auth login --email user@example.com --password secret
```

#### `nexus auth register`
Register a new account on the connected node.
```bash
nexus auth register --email user@example.com --password secret
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

### TUI Architecture

The NEXUS TUI is built on Textual and organized into four primary zones:

1. **Status Header**: Displays real-time telemetry, active version, authenticated identity (Google OAuth), connected Core API / Control Plane URL, active profile, and live latency ping.
2. **Navigation Sidebar**: Collapsible tree organized across the 8 canonical categories with command count badges.
3. **Command Explorer**: Live-filtered data table displaying available commands, arguments, safety ratings, and usage syntax.
4. **Context Panel**: Comprehensive documentation, syntax breakdown, argument types, destructive warnings, and quick execution trigger.

### Global Command Palette (`Ctrl+K` or `/`)

Press `/` or `Ctrl+K` from any screen to open the global Command Palette. Supports fuzzy search across all command names, token paths, descriptions, and categories.

### Keyboard Shortcuts Reference

| Key | Action |
| :--- | :--- |
| `/` or `Ctrl+K` | Open Global Command Palette & Fuzzy Search |
| `?` | Toggle Keyboard Shortcuts Help Sheet |
| `r` | Refresh Status Header & Connection Telemetry |
| `p` | Open Profile Switcher & Settings Dialog |
| `w` | Launch Guided Setup Wizard |
| `q` | Quit Application |
| `Tab` / `Shift+Tab` | Cycle focus between Sidebar, Explorer, and Filter Input |
| `Up` / `Down` | Navigate lists and table rows |
| `Enter` | Activate / Execute selected command |
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
