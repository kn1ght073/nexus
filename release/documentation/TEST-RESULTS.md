# NEXUS — Test Execution & Verification Report

**Date of Execution**: November 2026  
**Test Environment**: macOS Apple Silicon (`aarch64`), Python 3.11, Node.js 20, Rust 1.100.0  
**Overall Status**: **220 / 220 Tests Passing (100% Success Rate)**

---

## 1. Test Suite Summary

| Test Suite | Location | Tests Executed | Passed | Failed | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Core API Test Suite** | `services/core-api/tests` | 104 | 104 | 0 | ~6.5s |
| **Integration Test Suite** | `tests/` | 15 | 15 | 0 | ~1.0s |
| **CLI & TUI Test Suite** | `apps/cli/tests` | 88 | 88 | 0 | ~140.8s |
| **Mobile Companion Unit Tests** | `apps/mobile/tests` | 9 (4 suites) | 9 | 0 | ~3.8s |
| **macOS DMG Packaging** | `release/macos/NEXUS.dmg` | 2 (build + mount) | 2 | 0 | Verified |
| **Android APK Signing** | `release/mobile/NEXUS-android.apk`| 2 (build + sign) | 2 | 0 | Verified |
| **Total** | | **220** | **220** | **0** | **100%** |

---

## 2. Core API & Integration Test Coverage (`119 / 119 Passed`)
```text
services/core-api/tests/test_api.py .................................... [ 30%]
.......                                                                  [ 36%]
services/core-api/tests/test_client_console.py ........                  [ 42%]
services/core-api/tests/test_github.py .............                     [ 53%]
services/core-api/tests/test_online_access.py ........................   [ 73%]
services/core-api/tests/test_security_audit.py ................          [ 87%]
tests/test_google_auth_and_discovery.py ....                             [ 90%]
tests/test_unified_host_sync.py ...........                              [100%]
======================== 119 passed, 1 warning in 7.46s ========================
```
- **Authentication**: Google OAuth token exchange, refresh cycle, token revocation, rate limiting.
- **Files**: Jailed storage navigation, directory containment, path traversal rejection, content search, uploads, downloads.
- **Projects & Tasks**: Revision incrementing on mutation, soft-delete tombstones, ownership isolation.
- **Sync & Relay**: Incremental sync pulls, ASGI proxy frames, WebSocket real-time broadcast.

---

## 3. CLI & TUI Test Coverage (`88 / 88 Passed`)
```text
apps/cli/tests/test_auth_validation.py ......                            [  6%]
apps/cli/tests/test_cli_tui_dispatch.py ....                             [ 11%]
apps/cli/tests/test_client.py .......                                    [ 19%]
apps/cli/tests/test_commands.py ............                             [ 32%]
apps/cli/tests/test_config.py .....                                      [ 38%]
apps/cli/tests/test_host.py ...                                          [ 42%]
apps/cli/tests/test_profiles.py .....                                    [ 47%]
apps/cli/tests/test_project_drilldown.py ..........                      [ 59%]
apps/cli/tests/test_registry.py .......                                  [ 67%]
apps/cli/tests/test_tui.py ....                                          [ 71%]
apps/cli/tests/test_tui_views.py .........................               [100%]
======================== 88 passed in 140.83s (0:02:20) ========================
```
- **TUI Screens**: ActivityView, ProjectsKanban, TaskBoards, SovereignStore fallback.
- **Commands**: Host start/stop daemon, claiming node on control plane, profile management.

---

## 4. Mobile Companion Test Coverage (`9 / 9 Passed`)
```text
PASS tests/client.test.ts
PASS tests/theme.test.ts
PASS tests/secureStore.test.ts
PASS tests/workspaceStore.test.ts

Test Suites: 4 passed, 4 total
Tests:       9 passed, 9 total
Time:        3.795 s
```
- **Host Discovery**: Dual-tier probe algorithm (`probeLAN()` then `relayFallback()`).
- **SecureStore**: Keychain token encryption and retrieval.
- **State Store**: Workspace synchronization and conflict resolution.

---

## 5. Binary Artifact Verification

### macOS Disk Image (`NEXUS.dmg`)
- **Path**: `release/macos/NEXUS.dmg`
- **Size**: 3,348,200 bytes (~3.35 MB)
- **SHA-256**: `f743653ec6a655187d2f25805b995a95d39002c72edbb4c0e1132771f6a4ca30`
- **Mount Verification**: Tested via `hdiutil attach -nobrowse` -> CRC32 verified -> contains valid `NEXUS Desktop.app` and `Applications` symlink.

### Android Release APK (`NEXUS-android.apk`)
- **Path**: `release/mobile/NEXUS-android.apk`
- **Size**: 1,619,733 bytes (~1.62 MB)
- **SHA-256**: `d96994ce9bba05d03a5833f3e396e14b0943d9d1f58d05e8ad550416d4db4d88`
- **Signature Verification**: Signed with RSA-2048 key using `jarsigner` (SHA256withRSA) -> valid Android package ready for sideloading and testing.
