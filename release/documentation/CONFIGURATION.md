# NEXUS — Environment & Configuration Guide

This document details the configuration parameters, environment variables, storage paths, and network routing rules across the NEXUS ecosystem.

---

## 1. Storage & Database Paths

| Entity | Default Path | Environment Override | Description |
| :--- | :--- | :--- | :--- |
| **Authoritative Database** | `~/.nexus/nexus.db` | `NEXUS_DATABASE_URL` | Local SQLite 3 database on the primary Mac host. Holds canonical records for projects, tasks, notes, and file metadata. |
| **Jailed Storage Roots** | `~/Documents` | `NEXUS_STORAGE_ROOTS` | Semicolon or comma-separated directory paths where shared files are jailed. Traversal attempts are rejected with HTTP 403. |
| **CLI Config File** | `~/.nexus/cli_config.json` | `NEXUS_CLI_CONFIG` | Stores active host endpoint, claimed node ID, and session credentials for the CLI. |
| **Desktop App Data** | `~/Library/Application Support/local.nexus.desktop` | OS Defined | Local webview cache and keychain session identifiers for Tauri 2. |

---

## 2. Environment Variables Reference

### Core API (`services/core-api`)
```bash
# Network & Host
NEXUS_HOST="127.0.0.1"             # Host bind interface
NEXUS_PORT=8000                    # Host bind port
NEXUS_CANONICAL_PUBLIC_URL=""      # Public HTTPS URL if reverse-proxied

# Identity & Security
NEXUS_JWT_SECRET="<secret>"        # Ed25519 or HMAC secret for session token signing
NEXUS_GOOGLE_CLIENT_ID="<id>"      # Google OAuth 2.0 Web Client ID
NEXUS_GOOGLE_CLIENT_SECRET="<sec>" # Google OAuth 2.0 Client Secret
NEXUS_CONTROL_PLANE_MODE="false"   # Set "true" ONLY for hosted Render control plane (disables personal storage)

# Storage & Quotas
NEXUS_STORAGE_ROOTS="/Users/<user>/Documents" # Jailed directory root
NEXUS_MAX_SEARCH_DEPTH=6           # Maximum directory recursion depth for file search
NEXUS_MAX_SEARCH_RESULTS=50        # Maximum results returned from file content search
```

### Desktop App (`apps/desktop`)
Configurable directly within the application via **Settings -> Host Endpoint Routing**:
- `Local Mac Host`: `http://127.0.0.1:8000` (Default)
- `Cloud Relay Proxy`: `https://nexus-control-plane-uvi8.onrender.com`
- `Custom LAN Endpoint`: `http://<lan-ip>:8000`

### Mobile Companion (`apps/mobile`)
Configured in `app.json` and auto-negotiated at runtime:
- `EXPO_PUBLIC_CONTROL_PLANE_URL`: `https://nexus-control-plane-uvi8.onrender.com`
- `NEXUS_CORE_URL`: Auto-discovered from active claimed node (`lan_url` or `relay_proxy_url`).

---

## 3. Network Ports & Protocols

| Port / Protocol | Direction | Purpose | Security |
| :--- | :--- | :--- | :--- |
| `8000 / HTTP` | Inbound (LAN / Loopback) | Core REST API (Projects, Tasks, Notes, Files) | JWT Bearer Auth |
| `8000 / WS` | Inbound (LAN / Loopback) | Real-time domain event notification stream | Session Token handshake |
| `443 / WSS` | Outbound (Mac -> Render) | Node Bridge WebSocket tunnel for relay proxy | Ed25519 signed frames |
| `8443 / HTTPS` | Inbound (mDNS LAN) | Pinned self-signed TLS node endpoint | TLS 1.3 |
