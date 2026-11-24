# NEXUS Release — Installation & Operator Guide

This guide details the installation and execution procedure for the NEXUS personal digital command center across macOS Desktop, Android Mobile, and Headless Terminal CLI.

---

## 1. Primary Deliverable: macOS Desktop Application (`.dmg`)

### Artifact Information
- **Package**: `release/macos/NEXUS.dmg`
- **Architecture**: Universal macOS (Apple Silicon `aarch64` & Intel `x86_64`)
- **Checksum**: Verified in `release/macos/SHA256SUMS.txt`
- **Engine**: Tauri 2 Native Shell + React 18 Sovereign Command Center

### Installation Steps
1. Double-click `release/macos/NEXUS.dmg` to mount the disk image.
2. Drag `NEXUS Desktop.app` into the `Applications` folder shortcut.
3. Open `NEXUS Desktop` from `/Applications` or Spotlight (`Cmd + Space` -> "NEXUS Desktop").
   - *Note on macOS Gatekeeper*: Because this is a temporary internal research release, if prompted by Gatekeeper, right-click `NEXUS Desktop.app` -> select **Open** -> click **Open**.

### Host Lifecycle & Authoritative Database
- The macOS Desktop application communicates directly with the authoritative Core API instance on loopback (`http://127.0.0.1:8000`) or the cloud control plane relay (`https://nexus-control-plane-uvi8.onrender.com`).
- Personal application data (projects, tasks, notes, files) is stored authoritatively in the local SQLite database at:
  ```bash
  ~/.nexus/nexus.db
  ```
- To start the primary host daemon from terminal before or alongside the desktop UI:
  ```bash
  nexus host start
  # or directly via python:
  python3 -m uvicorn nexus_core.main:create_app --factory --host 127.0.0.1 --port 8000
  ```

---

## 2. Secondary Deliverable: Android Mobile Companion (`.apk`)

### Artifact Information
- **Package**: `release/mobile/NEXUS-android.apk`
- **Architecture**: Android 10.0+ (API level 29+)
- **Checksum**: Verified in `release/mobile/SHA256SUMS.txt`
- **Engine**: Expo / React Native with Hermes bytecode compilation and v1 JAR signature

### Installation Steps
1. Connect your Android device via USB with USB Debugging enabled, or transfer `NEXUS-android.apk` to device storage.
2. Install via ADB:
   ```bash
   adb install -r release/mobile/NEXUS-android.apk
   ```
   Or open the `.apk` file using the Android Files app and tap **Install**.
3. Launch **NEXUS Mobile** from your app drawer.

### Zero-Config Connection Flow
1. Tap **Continue with Google**.
2. Select your Google account.
3. NEXUS automatically performs background discovery:
   - Probes the local network (`http://<mac-ip>:8000`) for the active host claimed by your Google account.
   - If outside LAN, transparently routes through the encrypted cloud relay proxy (`https://nexus-control-plane-uvi8.onrender.com/api/relay/proxy`).
4. Projects, notes, and tasks immediately populate on your mobile dashboard.

---

## 3. Terminal CLI & Sovereign Power Tools

### Installation
Install the CLI in editable mode or from source:
```bash
# From repository root:
pip install -e ./apps/cli
```

### Essential CLI Operations
```bash
# Check CLI version and connection
nexus --help
nexus status

# Start sovereign host and claim node on control plane
nexus host start

# Launch interactive Terminal UI (TUI)
nexus tui

# List and create sovereign projects
nexus projects list
nexus projects create "Distributed Sync" --desc "Cross-client sync architecture"

# Manage tasks
nexus tasks list
nexus tasks add "Implement binary protocol" --project-id 1
nexus tasks done 1

# Manage notes
nexus notes list
nexus notes create "Architecture Review" --content "Mac holds authoritative SQLite state."
```
