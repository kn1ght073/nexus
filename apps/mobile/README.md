# NEXUS Mobile Companion (Expo SDK 58 + React Native 0.88)

Official mobile application for the NEXUS sovereign personal digital infrastructure ecosystem.

## Key Features

- **Expo SDK 58 & React Native 0.88**: Built for the latest official Expo release with React 19 concurrency and bridgeless TurboModules architecture.
- **Sovereign Cockpit Dashboard**: Live infrastructure status, active node indicator, device counters, and real-time audit event streams.
- **Google OAuth Authentication & Hardware Isolation**: OpenID Connect with PKCE S256, cryptographically random nonce/state, and hardware keychain isolation (`expo-secure-store`).
- **Hardware Fleet & Device Management**: Register mobile clients with scoped permissions, view device capabilities, track liveness, and revoke compromised sessions.
- **Node Pairing via QR Code & Numeric Passcodes**: Pair edge compute servers using the camera scanner or 6-digit one-time passcodes (`/api/pairing/exchange`).
- **Personal Workspace & Storage**: Full mobile management of Projects, Tasks (with daily deadlines and completion toggles), Notes (with tag indexing), and sandboxed Storage Roots browsing.
- **Incremental Sync Engine**: Delta synchronization pulling changes via server revisions (`/api/sync/pull`) with offline resilience.
- **Mobile Doctor Diagnostics**: End-to-end runtime diagnostic probes matching `nexus doctor`.
- **Adaptive Visual System**: Restrained deep charcoal & electric cyan styling with dark and light theme switching.

---

## Local Development & Setup

### Prerequisites

- Node.js 18+ (tested on Node v26)
- npm / yarn
- Expo Go App on Android / iOS (SDK 58 compatible)

### Install Dependencies

```bash
cd apps/mobile
npm install --legacy-peer-deps
```

### Typecheck & Test

```bash
npm run typecheck
npm test
```

### Run Locally

```bash
# Start Expo development server:
npm start

# Or launch directly on Android / iOS / Web:
npm run android
npm run ios
npm run web
```

---

## Architecture

```text
apps/mobile/
├── app/                  # Expo Router file-based routes
│   ├── _layout.tsx       # Theme, React Query, and Auth Providers
│   ├── (auth)/           # Onboarding, server endpoint selection, Google OAuth
│   └── (app)/            # Cockpit, Devices, Nodes, Workspace, Sync, Settings
├── src/
│   ├── api/              # Typed client with token rotation & 401 interceptor
│   ├── components/       # Card, Button, Input, MetricBox, StatusBadge, EmptyState
│   ├── context/          # AuthContext and ThemeContext
│   ├── theme/            # Color palettes and semantic design tokens
│   └── utils/            # Platform-backed SecureStore wrapper
└── tests/                # Jest unit and integration test suite
```
