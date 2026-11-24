# NEXUS — Unified Local-First Host, Mobile Pairing & Sync Architecture

This operational guide details the architecture, configuration, and verification procedures for running NEXUS as a **single unified, local-first personal infrastructure ecosystem** anchored by a primary **Mac Host**.

---

## 1. Intended Architecture & Data Flow

```text
                                  ┌───────────────────────────┐
                                  │   Cloud Control Plane     │
                                  │   (Render / Free Tier)    │
                                  │                           │
                                  │  • Identity & Google Auth │
                                  │  • Ephemeral Relay Bridge │
                                  │  • Zero Personal Content  │
                                  └─────────────┬─────────────┘
                                                │
                                    Device Coordination
                                                │
                    ════════════════════════════╪════════════════════════════
                                PRIVATE LAN / ENCRYPTED LINK
                    ════════════════════════════╪════════════════════════════
                                                │
                                  ┌─────────────▼─────────────┐
                                  │     NEXUS MAC HOST        │
                                  │     (Primary Machine)     │
                                  │                           │
                                  │  • Core API (Node Mode)   │
                                  │  • Authoritative SQLite   │
                                  │    (~/.nexus/nexus.db)    │
                                  │  • PRAGMA foreign_keys=ON │
                                  │  • PRAGMA journal_mode=WAL│
                                  │  • Device Authorization   │
                                  │  • Projects, Tasks, Notes │
                                  └──────┬─────────────┬──────┘
                                         │             │
                              Direct LAN │             │ Direct LAN / Relay
                             HTTP / JSON │             │ HTTP / JSON
                                         │             │
                                  ┌──────▼──────┐ ┌────▼────────┐
                                  │ Terminal /  │ │   Mobile    │
                                  │ Desktop CLI │ │   Client    │
                                  │  Cockpit    │ │  (Expo iOS/ │
                                  │             │ │   Android)  │
                                  └─────────────┘ └─────────────┘
```

### Key Principles
1. **One Authoritative Source of Truth**: The active NEXUS Host (Mac) maintains the canonical SQLite database at `~/.nexus/nexus.db`. All creations, edits, and deletions from connected clients immediately write to this host.
2. **Absolute Data Sovereignty**: Personal application data (projects, tasks, notes, files) is strictly stored on the local host machine. The cloud control plane (Render) acts purely as an identity and coordination registry; it never receives, parses, or persists unencrypted personal application data.
3. **Cross-Platform Host Readiness**: The backend runs standard Python 3.11+ and SQLite with WAL mode. In the future, a Windows machine can become the primary host simply by starting `nexus host start` with no architectural redesign.

---

## 2. Host Commands on macOS

The NEXUS CLI provides a dedicated `nexus host` command suite:

### Start the Host
```bash
# Start on LAN in background mode (recommended for daily operation)
nexus host start --host 0.0.0.0 --port 8000 --daemon

# Start in foreground for debugging
nexus host start --host 0.0.0.0 --port 8000

# Start in local-only development mode (loopback only)
nexus host start --host 127.0.0.1 --port 8000
```
- **Bind address**: `0.0.0.0` binds to all interfaces, allowing mobile devices on your Wi-Fi network to connect.
- **Persistent Database**: Automatically anchored to `~/.nexus/nexus.db` with SQLite WAL mode enabled.
- **Port**: Default `8000` (customizable via `--port`).

### Check Host Telemetry
```bash
nexus host status
```
Outputs live telemetry:
- Online/offline state and daemon PID.
- Hostname and OS platform (`Darwin`).
- Local loopback URL (`http://127.0.0.1:8000`).
- Direct LAN URL for mobile companion (`http://192.168.x.x:8000`).
- Database engine, file path, and database size in KB.
- Active counts of projects, tasks, notes, and paired devices.

### Generate Mobile Pairing Credentials & QR Code
```bash
nexus host pair
```
Generates:
1. Terminal ASCII QR code encoding `nexus://pair?url=http://<mac-ip>:8000&code=<pin>&name=<host>`.
2. 6-digit numeric pairing PIN.
3. Direct mobile pairing URL.

### Stop the Host
```bash
nexus host stop
```
Safely terminates the running background daemon and cleans up PID tracking files.

---

## 3. Mobile Client Connection Walkthrough

To connect the NEXUS Mobile Companion (Expo app) to your Mac Host:

### Method A — Direct LAN Host Configuration
1. Open the NEXUS Mobile App on your iPhone or Android device (connected to the same Wi-Fi network as your Mac).
2. Navigate to **Settings** > **Primary NEXUS Host (Mac)**.
3. In the Host Address input, enter your Mac's LAN address (e.g. `http://192.168.1.15:8000` as reported by `nexus host status`).
4. Tap **Test Reachability**:
   - The app probes `/health` and `/api/host/status`.
   - On success, it displays: `✓ Connected to nexus-host (node) in 18ms. Ready for cross-device sync.`
5. Tap **Save & Connect**:
   - The app routes all workspace queries (`/api/projects`, `/api/tasks`, `/api/notes`, `/api/files`) directly to your Mac Host.

### Method B — QR Code / One-Time Numeric PIN Pairing
1. On your Mac terminal, run:
   ```bash
   nexus host pair
   ```
2. On your mobile app, navigate to **Nodes** > **Pair Edge Node**.
3. Either:
   - Point your camera at the terminal QR code, OR
   - Enter the 6-digit pairing PIN and tap **Complete Pairing**.

---

## 4. Honest Disconnection & Offline Handling

When the Mac Host is offline or the mobile device leaves the local Wi-Fi network:

- **No False Assurances**: The app will not falsely claim items are saved to the remote host.
- **Visual Disconnected Banner**: The top of the Workspace views (Projects, Tasks, Notes) displays:
  ```text
  ⚠️ Mac Host Disconnected · Displaying cached data (Last synced: 14:32:05)
  ```
- **Local Buffer Fallback**: If you create or edit items while disconnected, they are stored safely in the device's local buffer with a pending-sync indicator.
- **Automatic Reconnection**: As soon as your mobile device reconnects to your Mac's LAN network, pull-to-refresh reconciles changes with the host.

---

## 5. Automated Verification Baseline

All 10 cross-device synchronization scenarios are automatically verified by the integration test suite in `tests/test_unified_host_sync.py`:

```bash
# Execute the full cross-device acceptance suite
PYTHONPATH=services/core-api services/core-api/.venv/bin/pytest tests/test_unified_host_sync.py -v
```

| Scenario | Description | Status |
|---|---|---|
| **Scenario 1** | Host boot in node mode with SQLite WAL mode and foreign keys enabled | `PASSED` |
| **Scenario 2** | Mac client creates Project P1 -> written to host SQLite database | `PASSED` |
| **Scenario 3** | Mobile client connects to Mac Host -> queries `/api/projects` -> sees P1 | `PASSED` |
| **Scenario 4** | Mobile client creates Project P2 -> persisted directly in Mac Host SQLite | `PASSED` |
| **Scenario 5** | Mac / CLI queries `/api/projects` -> immediately sees Project P2 from mobile | `PASSED` |
| **Scenario 6** | Mobile updates P1 title -> host validates and bumps revision cursor | `PASSED` |
| **Scenario 7** | Mac / CLI queries P1 -> receives updated title and higher revision | `PASSED` |
| **Scenario 8** | Mobile deletes P2 -> host records soft-deletion tombstone | `PASSED` |
| **Scenario 9** | Mac queries active projects -> P2 is not returned; no phantom reappearance | `PASSED` |
| **Scenario 10**| Host process restart simulation -> SQLite database retains all data across reboot | `PASSED` |

---

## 6. macOS Firewall Guidance

If your mobile device fails to reach your Mac Host:
1. Open **System Settings** > **Network** > **Firewall** on your Mac.
2. Ensure incoming connections are permitted for `python` or Python virtual environment binaries.
3. If using an interactive packet filter (`pfctl` / Little Snitch), permit inbound TCP connections on port `8000`.
