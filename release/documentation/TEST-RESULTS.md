# NEXUS — Test Execution & Verification Report

**Date of Execution**: November 25, 2026  
**Test Environment**: macOS Apple Silicon (`aarch64`), Python 3.11, Node.js 20+, Rust 1.100.0, Android SDK 36/37 (`AlloyPlayer` emulator)  
**Overall Status**: **227 / 227 Automated Tests + Binary Installations Passing (100%)**

---

## 1. Test Suite Summary

| Test Suite | Location | Tests Executed | Passed | Failed | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Core API Test Suite** | `services/core-api/tests` | 104 | 104 | 0 | 6.71s |
| **Unified Sync & Auth Integration** | `tests/test_google_auth_and_discovery.py`, `tests/test_unified_host_sync.py` | 15 | 15 | 0 | 2.03s |
| **CP Token Exchange & Relay Auth** | `tests/test_cp_exchange.py` | 3 | 3 | 0 | 0.89s |
| **CLI & TUI Test Suite** | `apps/cli/tests` | 88 | 88 | 0 | 141.39s |
| **Desktop API & Auth Fallback Suite** | `apps/desktop/src/api.test.ts` | 8 | 8 | 0 | <1s |
| **Mobile Companion Unit & Typecheck** | `apps/mobile/tests` | 9 (4 suites) | 9 | 0 | 2.72s |
| **Total Automated Tests** | | **227** | **227** | **0** | **100%** |

---

## 2. Core API & Integration Test Coverage (`122 / 122 Passed`)
```text
services/core-api/tests/test_api.py .................................... [ 34%]
.......                                                                  [ 41%]
services/core-api/tests/test_client_console.py ........                  [ 49%]
services/core-api/tests/test_github.py .............                     [ 61%]
services/core-api/tests/test_online_access.py ........................   [ 84%]
services/core-api/tests/test_security_audit.py ................          [100%]
======================== 104 passed, 1 warning in 6.71s ========================

tests/test_google_auth_and_discovery.py ....                             [ 26%]
tests/test_unified_host_sync.py ...........                              [100%]
======================== 15 passed, 1 warning in 2.03s =========================

tests/test_cp_exchange.py ...                                            [100%]
========================= 3 passed, 1 warning in 0.89s =========================
```
- Verified `POST /api/auth/cp-exchange` server-to-server Control-Plane verification, local SQLite user provisioning, `PATCH /api/projects/{project_id}`, `X-Nexus-Node-Authorization` relay promotion, and jailed file upload/download/search.

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
======================== 88 passed in 141.39s (0:02:21) ========================
```

---

## 4. Desktop & Mobile Unit Tests (`17 / 17 Passed`)
```text
> nexus-desktop@0.1.0 test (8 passed):
  cleanToken, normalizeBaseUrl, isLocalUrl/isCloudUrl, setBaseUrl/getBaseUrl,
  cloud login + cp-exchange to local Mac host, relay fallback proxy + dual auth headers,
  offline host blocks 404 control-plane calls cleanly, bad token clears session

> nexus-mobile@0.1.0 typecheck & test (4 suites, 9 passed):
  PASS tests/theme.test.ts
  PASS tests/secureStore.test.ts
  PASS tests/client.test.ts
  PASS tests/workspaceStore.test.ts
```

---

## 5. Binary Artifact & Runtime Verification

### macOS Disk Image (`NEXUS.dmg`)
- **Path**: `release/macos/NEXUS.dmg`
- **Size**: `3,360,403` bytes (~3.2 MiB)
- **SHA-256**: `8f323fb436599de6d2bb958aef078fc2cb2d4a82e9d96740d2b2854c232d828a`
- **Bundle Signature**: Sealed with `codesign --force --deep --sign -` (`Contents/_CodeSignature/CodeResources` verified). `codesign --verify --deep --strict` inside mounted DMG reported `valid on disk` and `satisfies its Designated Requirement`.
- **Launch Check**: Extracted `NEXUS Desktop.app` from DMG and launched cleanly on macOS (`nexus-desktop` process verified active).

### Android Release APK (`NEXUS-android.apk`)
- **Path**: `release/mobile/NEXUS-android.apk`
- **Size**: `50,448,229` bytes (~48.1 MiB)
- **SHA-256**: `ccf464b21d91f41318a66764ef56359fd09f72828ad4bb93c8ca00f754059cda`
- **Signature Verification**: `apksigner verify` passed (`Verified using v2 scheme (APK Signature Scheme v2): true`).
- **Emulator Installation & Launch**: `adb install -r release/mobile/NEXUS-android.apk` succeeded on Android API 36 emulator (`AlloyPlayer`); `local.nexus.mobile/.MainActivity` started cleanly (PID verified active after 6s, zero runtime errors in `logcat`, visually verified welcome screen render).
