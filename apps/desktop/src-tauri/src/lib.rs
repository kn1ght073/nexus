//! NEXUS Desktop — Tauri 2 shell.
//!
//! The desktop app is a pure client of the NEXUS Core API (REST + WebSocket);
//! all state lives on the Node. This shell currently provides:
//! - `core_health` / `core_base_url`: resolve and probe the Core
//! - token storage in the OS keychain is planned (see progress.md step 4)
//!
//! Build instructions: see apps/desktop/README.md.

use serde::Serialize;

#[derive(Serialize)]
pub struct HealthStatus {
    pub ok: bool,
    pub detail: String,
}

/// Base URL of the NEXUS Core. In dev the Core runs on loopback; for LAN
/// deployment the Core advertises itself over mDNS as nexus.local:8443.
const CORE_URL: &str = "https://nexus-control-plane-uvi8.onrender.com";

#[tauri::command]
fn core_base_url() -> String {
    CORE_URL.to_string()
}

#[tauri::command]
async fn core_health(base_url: Option<String>) -> HealthStatus {
    let url = format!("{}/health", base_url.unwrap_or_else(|| CORE_URL.to_string()));
    // surf/reqwest intentionally omitted from the skeleton: the frontend
    // performs health checks itself via fetch (same-origin policy handled by
    // the Core's CORS allowlist). This command exists as the Rust-side hook
    // for future tray/service integration.
    HealthStatus {
        ok: false,
        detail: format!("probe from Rust not wired yet; frontend fetches {} directly", url),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![core_base_url, core_health])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
