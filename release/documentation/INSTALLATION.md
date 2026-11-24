# NEXUS Release — Installation & Operator Guide

This guide details the installation and execution procedure for the NEXUS personal digital command center across macOS Desktop, Android Mobile, and Headless Terminal CLI.

---

## 1. Primary Deliverable: macOS Desktop Application (`.dmg`)

### Artifact Information
- **Package**: `release/macos/NEXUS.dmg`
- **Architecture**: Apple Silicon (`aarch64-apple-darwin`)
- **Checksum**: Verified in `release/macos/SHA256SUMS.txt`
- **Engine**: Tauri 2 Native Shell + React 18 Sovereign Command Center

### Installation Steps
1. Double-click `release/macos/NEXUS.dmg` to mount the disk image.
2. Drag `NEXUS Desktop.app` into the `Applications` folder shortcut.
3. Open `NEXUS Desktop` from `/Applications` or Spotlight (`Cmd + Space` -> "NEXUS Desktop").
   - *Note on macOS Gatekeeper*: Because this temporary release uses an ad-hoc signature rather than an Apple Developer ID notarized certificate, macOS may quarantine browser-downloaded copies. Right-click `/Applications/NEXUS Desktop.app` -> **Open** (or clear the download attribute once with `xattr -cr "/Applications/NEXUS Desktop.app"`).

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
- **Architecture**: Android (`arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64`, API level 24–36)
- **Checksum**: Verified in `release/mobile/SHA256SUMS.txt`
- **Engine**: Expo SDK 58 / React Native 0.88.1 with Hermes bytecode compilation and APK Signature Scheme v2

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
