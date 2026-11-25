# NEXUS Mobile Companion — Build Information

- **Product Name**: NEXUS Mobile
- **Application ID / Package**: `local.nexus.mobile`
- **Version**: `0.1.0` (Temporary Release Candidate)
- **Target Platform**: Android 10.0+ (API level 24–36, compiled SDK 37, target SDK 36)
- **ABIs Included**: `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64`
- **Runtime Engine**: Expo SDK 58 / React Native 0.88.1 with Hermes Bytecode Engine (`expo.useLegacyPackaging=true`)
- **Package Format**: Compiled Android Release Package (`.apk`) built via Gradle `assembleRelease`
- **Signature**: Signed with APK Signature Scheme v2 (`apksigner verify` passed)
- **Runtime Verification**: Installed and launched on Android API 36 emulator (`AlloyPlayer`), confirmed rendering `NEXUS` welcome screen cleanly with zero crashes
- **SHA-256 Checksum**: `2a71bf0868f9203cb58d92ff9214f303982c4e7fdceb4a5446dc7fe3adfee8ea` (`NEXUS-android.apk`)
