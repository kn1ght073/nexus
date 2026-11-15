# NEXUS Mobile (Android) — scaffold

The capture & control client (Minor project 2): Kotlin + Jetpack Compose,
talking REST to the NEXUS Core API on the Windows Node. Offline-friendly by
design (Room cache + revision-based sync are the next milestone — see the
root `progress.md`).

> **Status**: source scaffold — login, quick-capture task list, task
> completion wired to the real Core endpoints; tokens in
> EncryptedSharedPreferences. Build locally in Android Studio.

## Build & run (dev)

```bash
# 1. Core on the Windows Node (or your dev machine):
cd ../../services/core-api
uvicorn nexus_core.main:app --host 0.0.0.0 --port 8000   # LAN bind

# 2. Phone + dev PC on the same LAN; then in Android Studio:
#    open apps/mobile, set NEXUS_CORE_URL in app/build.gradle.kts to
#    http://<your-dev-pc-ip>:8000  (or use adb reverse for loopback)
adb reverse tcp:8000 tcp:8000     # loopback alternative

# 3. Build:
gradle wrapper --gradle-version 8.9   # first time only (wrapper not committed)
./gradlew :app:assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

LAN TLS deployment (production): the Node runs `https://nexus.local:8443`
with a self-signed CA. Export the CA, drop it at
`app/src/main/res/raw/nexus_node_ca.pem`, and uncomment the trust-anchors
block in `res/xml/network_security_config.xml` (pairing flow, plan §5).

## Layout

```text
apps/mobile/
├── settings.gradle.kts · build.gradle.kts · gradle/libs.versions.toml  # AGP 8.5 / Kotlin 2.0 / Compose BOM
└── app/
    ├── build.gradle.kts           # deps: retrofit+moshi, okhttp, room, datastore, security-crypto
    ├── proguard-rules.pro
    └── src/main/
        ├── AndroidManifest.xml    # INTERNET + RECORD_AUDIO; networkSecurityConfig
        ├── res/xml/network_security_config.xml  # loopback cleartext for dev; LAN CA pinning
        ├── res/values/            # strings, theme
        └── java/local/nexus/mobile/
            ├── MainActivity.kt    # Compose entry: login or tasks
            ├── api/NexusApi.kt    # Retrofit interface + DTOs (auth, tasks, notes, devices)
            ├── data/TokenStore.kt # EncryptedSharedPreferences token store + core URL
            └── ui/ViewModels.kt   # LoginViewModel, TasksViewModel + screens
```

## Next milestones (see progress.md)

1. Room offline cache of tasks/notes/… + `/sync/pull` since-revision cursor +
   `/sync/push` on reconnect (the sync engine landed in Core step 2)
2. Voice capture: MediaRecorder → POST /inbox job → Node Whisper STT
3. Foreground-service WebSocket for live notifications (LAN-only, no FCM)
4. Camera/file upload via the chunked file-sync API
