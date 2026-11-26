# NEXUS macOS Desktop — Build Information

- **Product Name**: NEXUS Desktop
- **Bundle ID**: `local.nexus.desktop`
- **Version**: `0.1.0` (Temporary Release Candidate)
- **Target Architecture**: Apple Silicon (`aarch64-apple-darwin`)
- **Shell Engine**: Tauri 2 (Rust 1.100.0, `@tauri-apps/cli` v2.12.6, `@tauri-apps/api` v2.12.5)
- **Frontend Stack**: React 18, Vite 6, TypeScript 5.6
- **Package Format**: Apple Disk Image (`.dmg` UDZO compressed) & Application Bundle (`.app`)
- **Signing Status**: Ad-hoc bundle signature (`codesign --force --deep --sign -`), verified with `codesign --verify --deep --strict`. Apple Developer ID notarization is not configured on this build machine.
- **SHA-256 Checksum**: `e68ca75e2a9d38a3b3c631d1177e066a15c7c570b2412838a6c05964db01906a` (`NEXUS.dmg`)
