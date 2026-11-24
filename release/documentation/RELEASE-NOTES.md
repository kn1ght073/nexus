# NEXUS Temporary Stable Release — Release Notes (v0.1.0-alpha)

**Release Date**: November 2026  
**Build Scope**: macOS Universal Desktop DMG, Android Companion APK, Unified Core API & CLI  
**Data Sovereignty**: Strict Local-First Architecture (Primary Mac Host + SQLite Database)

---

## Executive Summary
This temporary release unifies the NEXUS personal digital command center into **one synchronized ecosystem** across three distinct operational surfaces:
1. **macOS Desktop (`.dmg`)**: Primary operator command center with full project, task, note, and jailed file management.
2. **Android Mobile (`.apk`)**: Companion client with automated Google OAuth discovery and dual-tier routing (LAN direct + encrypted relay fallback).
3. **Terminal CLI (`nexus`)**: Headless operator suite featuring Rich TUI, background host orchestration, and automated node claim bridge.

---

## Architecture & Data Flow
- **Primary Source of Truth**: The local SQLite database running on the user's Mac (`~/.nexus/nexus.db`).
- **Zero-Knowledge Control Plane**: The hosted Render instance functions purely as an identity coordinator and encrypted transit relay. Personal application data (projects, tasks, notes, files) is never persisted unencrypted in the cloud.
- **Dual-Tier Connection**:
  1. *Tier 1 (LAN)*: Direct WebSocket / HTTP over local subnet (`http://<mac-ip>:8000`).
  2. *Tier 2 (Relay)*: End-to-end encrypted ASGI WebSocket tunnel over Render control plane (`/api/relay/{node_id}/proxy`).

---

## Deliverables in This Release

| Component | Path | Format | Description |
| :--- | :--- | :--- | :--- |
| **macOS Desktop** | `release/macos/NEXUS.dmg` | Apple DMG (UDZO) | Native macOS application with Tauri 2 + React 18 |
| **macOS Checksum** | `release/macos/SHA256SUMS.txt` | Text (SHA-256) | Cryptographic integrity verification |
| **Android Mobile** | `release/mobile/NEXUS-android.apk` | Signed APK (v1 JAR) | Mobile companion with Hermes bytecode & Google OAuth |
| **Android Checksum** | `release/mobile/SHA256SUMS.txt` | Text (SHA-256) | Cryptographic integrity verification |
| **CLI Client** | `apps/cli` | Python Package | Headless operator daemon & interactive TUI |
| **Documentation** | `release/documentation/` | Markdown | Comprehensive Installation, Demo Guide, and Test Suite |

---

## Detailed Component Highlights

### 1. macOS Desktop (`apps/desktop`)
- Native macOS menu and windowing built with Tauri 2.
- **Dashboard**: Real-time ping metrics, authoritative SQLite storage indicator, stats grid, and live audit feed.
- **Projects**: Sovereign project management with status transitions (`ACTIVE`, `COMPLETED`, `ARCHIVED`) and drilldown drawers.
- **Tasks**: Priority execution board with project tagging and instant status toggles.
- **Notes Wall**: Markdown-capable sovereign notes linked to projects.
- **Shared Files**: Jailed storage explorer supporting drag-and-drop file upload, content search, and direct downloads.
- **Devices & Host**: Active node status, registered companion device management, and mobile pairing guides.
- **Settings**: Dynamic endpoint switching (Local Mac Host vs Control Plane Relay vs Custom LAN).

### 2. Android Mobile Companion (`apps/mobile`)
- Built with Expo SDK 52 and Hermes engine.
- Automated Google Sign-In with browser session resilience.
- `autoDiscoverHost()` probes active claimed Mac node over LAN before falling back to relay proxy.
- Full offline-first cache via SQLite and Expo SecureStore.

### 3. Core API Enhancements (`services/core-api`)
- Direct Google ID token exchange endpoints: `POST /api/auth/google/token` and `POST /api/auth/google/id-token`.
- Reverse-proxy tunnel routes: `/api/relay/proxy` and `/api/relay/{node_id}/proxy`.
- Safe jailed file upload, download, and delete endpoints in `nexus_core/routers/files.py`.
- Revision tracking discipline bumped across all entities for reliable synchronization.
