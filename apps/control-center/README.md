# NEXUS Control Center

A modern, secure, and production-ready operator control console for the NEXUS distributed system.

Built as an independent Next.js App Router application deployed separately from the authoritative FastAPI Core API and Neon PostgreSQL transactional store.

---

## Architecture & Security Doctrine

```
                        ┌──────────────────────────────────────────────┐
                        │           NEXUS Control Center               │
                        │           (Next.js 16 App Router)           │
                        │   - Server Components SSR Data Ingestion     │
                        │   - Route Handlers BFF Layer                 │
                        │   - HttpOnly Strict Session Management       │
                        │   - Zero Client-Side Secret Leakage          │
                        └──────────────────────┬───────────────────────┘
                                               │ (Encrypted HTTPS)
                                               │ Cookie Forwarding (BFF)
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │              NEXUS Core API                  │
                        │            (FastAPI / Python 3.12)           │
                        │   - Authoritative Token Issuance & Rotation  │
                        │   - Lineage Replay Detection                 │
                        │   - RBAC Enforcement (Owner/Operator/User)   │
                        │   - Device & Node Coordination               │
                        │   - WebSocket Relay Mesh Multiplexing        │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │             Neon PostgreSQL DB               │
                        └──────────────────────────────────────────────┘
```

### Security Controls (Remediation Matrix Verified)
- **Zero Token Leakage**: JWT access and refresh tokens are strictly stored in `HttpOnly`, `SameSite=Lax`, `Secure` cookies managed by Next.js Route Handlers. Client-side JavaScript has zero access to raw bearer tokens, eliminating XSS token theft vectors.
- **Cryptographic Token Family Rotation**: Single-use refresh token exchange with lineage tracking. If a previously retired token is reused (indicating token replay or exfiltration), the control plane immediately revokes the entire session lineage.
- **Google OIDC Gate with PKCE**: PKCE S256 code challenge with cryptographically bound `state` and `nonce`. Identity is resolved by immutable `(issuer, sub)` tuples with optional email allowlist domain gating.
- **Granular RBAC**: Tiered access levels (`user`, `operator`, `owner`). Sensitive administrative actions (role updates, operator management) are strictly guarded on both server and client layers.

---

## 9 Core Views

1. **System Overview (`/`)**: Real-time cluster health, PostgreSQL database latency telemetry, registered fleet summary, active WebSocket relay sockets, and recent activity stream.
2. **Devices & Nodes (`/devices`)**: Fleet management supporting filtering by platform (`Windows`, `macOS`, `Android`, `Linux`, `CLI`), search filtering, device capability assignment, device revocation, and active node heartbeat inspection.
3. **Connections & Relay (`/relay`)**: Multiplexed WebSocket/TCP relay mesh monitor, attached sockets, and tunnel attachment protocol guides.
4. **Services & Health (`/services`)**: Passive inspection of local node AI services (STT `faster-whisper`, LLM `ollama`) and machine-readable runtime setup plans (`uv` vs `pip`).
5. **Security Center (`/security`)**: Compliance dashboard tracking remediation status for all 8 audit vulnerabilities (CORS, traversal, SQLi, perimeter separation, session rotation, brute-force lockout, relay authorization, and audit logging).
6. **Audit Logs (`/audit`)**: Append-only tamper-evident event stream with categorized filtering and instant JSON export.
7. **Sessions & Identity (`/sessions`)**: Server-side active session inventory with IP resolution, client classification, and one-click session lineage revocation.
8. **Settings (`/settings`)**: Control plane runtime parameters, environment coordination, database health, and operator profile.
9. **Operator Management (`/operators`)**: Elevated RBAC management table allowing owners to promote or demote operators with safeguards preventing owner lockout.

---

## Local Development

### Prerequisites
- Node.js 20+ (recommended: Node 22)
- npm 10+
- Running instance of NEXUS Core API (or live cloud instance)

### Installation
```bash
# Navigate to control center app
cd apps/control-center

# Install dependencies (0 audit vulnerabilities)
npm install
```

### Configuration
Create a `.env.local` file based on `.env.example`:
```env
# URL of authoritative FastAPI Core API
NEXUS_API_BASE_URL=https://nexus-control-plane-uvi8.onrender.com

# Port configuration
PORT=3000
NODE_ENV=development
```

### Commands
```bash
# Run local dev server with Turbopack
npm run dev

# Run unit tests (Vitest)
npm test

# Build production bundle
npm run build

# Start production server
npm start
```

---

## Render Deployment Guide

The NEXUS Control Center is designed to be hosted as a **Render Web Service** completely independent from the FastAPI Core API.

### Step 1: Create a New Web Service on Render
1. Go to the [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Select your GitHub repository: `kn1ght073/nexus`.

### Step 2: Configure Service Parameters
- **Name**: `nexus-control-center` (or your preferred name)
- **Region**: Same region as your Core API (e.g., `Oregon` or `Frankfurt`) for lowest internal latency
- **Branch**: `main` (or your deployment branch)
- **Root Directory**: `apps/control-center`
- **Runtime**: `Node`
- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm start`
- **Plan**: `Free` or `Starter`

### Step 3: Configure Environment Variables
In the **Environment** tab, set:
| Key | Value | Description |
|---|---|---|
| `NODE_VERSION` | `22.13.0` | Node.js runtime version |
| `NEXUS_API_BASE_URL` | `https://nexus-control-plane-uvi8.onrender.com` | Public or internal URL of the FastAPI Core API |
| `NODE_ENV` | `production` | Production mode |

### Step 4: CORS Configuration on Core API
Ensure your Core API's `NEXUS_CORS_ORIGINS` environment variable includes your Render Web Service URL:
```env
NEXUS_CORS_ORIGINS=https://nexus-control-center.onrender.com,http://localhost:3000
```

### Step 5: Deploy
Click **Create Web Service**. Render will install dependencies, build the Next.js production bundle, and start the service.
