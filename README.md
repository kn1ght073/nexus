# NEXUS — Personal Digital Infrastructure

A unified personal computing ecosystem for managing work, files, devices, media,
automation, and local AI across Windows, macOS, Android, and the terminal —
**fully inside your sovereign network**.

## Repository layout

```text
nexus/
├── apps/
│   ├── cli/          # NEXUS CLI & Cockpit TUI (Python 3.10+, Typer + Rich + Textual)
│   ├── desktop/      # NEXUS Desktop (Tauri 2 + Vite + React)
│   └── mobile/       # NEXUS Mobile (React Native / Expo)
├── services/
│   └── core-api/     # NEXUS Core API — FastAPI + SQLAlchemy + SQLite / Neon Postgres
├── docs/             # Showcase portal, architecture, proposals, and QA plans
└── tests/            # Test suites
```

## Quick start

### 1. Install NEXUS CLI (Direct from GitHub)

Install the standalone CLI directly into your environment or isolated with `pipx` / `uv` with zero PyPI dependencies:

```bash
# Direct install via pip:
pip install git+https://github.com/kn1ght073/nexus.git

# Or isolated installation via pipx (recommended):
pipx install git+https://github.com/kn1ght073/nexus.git

# Or via uv:
uv tool install git+https://github.com/kn1ght073/nexus.git
```

Verify your installation:
```bash
nexus --version
nexus doctor
```

### 2. Launch the Full-Screen Cockpit TUI

Simply launch `nexus` in your terminal to open the interactive sovereign control cockpit:

```bash
nexus
```

*Features: 10 dedicated workspace views (Overview, Account & Identity, Devices, Nodes, Relays, Storage, Notes & Tasks, Services, Diagnostics, Settings), instant command explorer, keyboard/mouse navigation, and dynamic dark/synthwave/light themes.*

---

### 3. Traditional CLI Usage & Quickstart

Normal headless CLI commands continue to work out of the box:

```bash
# Connect to your Core API or Live Control Plane
nexus config set-url https://nexus-control-plane-uvi8.onrender.com

# Authenticate via Google OAuth (opens secure browser flow or accepts token)
nexus login
# Or pass session token directly:
# nexus login --token <SESSION_TOKEN>

# Check health and identity
nexus status
nexus whoami

# Manage sovereign data
nexus project create "Sovereign Infrastructure"
nexus task add "Audit Syscall Stubs" 1
nexus task today
nexus devices list

# Deep system diagnostics
nexus doctor
```

---

### 4. Self-Hosting Core Node (Local Backend)

```bash
cd services/core-api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn nexus_core.main:app --reload                # dev: 127.0.0.1:8000
# LAN deployment (macOS/Android/CLI from other machines):
#   NEXUS_HOST=0.0.0.0 uvicorn nexus_core.main:app + firewall rule for the private profile
```

- Live Control Plane API: `https://nexus-control-plane-uvi8.onrender.com`
- Client Web Console: `https://nexus-control-plane-uvi8.onrender.com/client`
- Operator Control Center: `https://nexus-control-plane-uvi8.onrender.com/admin`
- Health Probe: `https://nexus-control-plane-uvi8.onrender.com/health`

---

### 5. Run the Test Suites

```bash
# Core API test suite (104 tests)
cd services/core-api && pytest tests/ -q

# CLI test suite (75 tests)
PYTHONPATH=apps/cli pytest apps/cli/tests/ -q
```

## Online access (control plane + secure relay)

Log in from anywhere, promote any machine as your main server, and pair
phones with **zero open ports** — full guide:
[`docs/deploy/online-access.md`](docs/deploy/online-access.md).

```bash
# one-time setup — the app sets up its own environment
nexus bootstrap

# control plane connection
nexus cp set https://nexus-control-plane-uvi8.onrender.com
nexus cp login

# promote THIS machine as the main server (any user, any OS)
nexus node claim --name "Workstation-01"

# pair a client / phone
nexus node pair

# local AI services
nexus services status
nexus services install stt                   # faster-whisper (voice notes)
```

The control plane coordinates identity and socket handshakes only — never tasks,
notes, files, or transcripts. Devices reach the node through an
end-to-end sealed relay (X25519 ECDH + ChaCha20-Poly1305); the relay host cannot read
payload frames.

## Security posture

- **Google OAuth Only**: Enforced sovereign account security; password-based account registration is completely disabled across all entrypoints.
- **Hardware Keystore Isolation**: OS Keyring backing on Windows (Credential Manager), macOS (Keychain), and Linux (SecretService) with secure file fallback.
- **Granular Ownership Isolation**: Every query ownership-filtered; per-user isolation strictly verified.
- **Sandboxed Storage**: File operations jailed to configured roots (`NEXUS_STORAGE_ROOTS`). Traversal blocked.
- **Zero Cloud Storage**: Files, documents, audio notes, and embeddings remain strictly on local edge nodes.

## License

Personal academic project — released under the MIT Open Source License.
