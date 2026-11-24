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

#[tauri::command]
fn open_browser_url(url: String) -> Result<(), String> {
    if !url.starts_with("https://") && !url.starts_with("http://") {
        return Err("Only http and https URLs are allowed".to_string());
    }
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("/usr/bin/open")
            .arg(&url)
            .spawn()
            .map_err(|e| format!("Failed to open browser on macOS: {}", e))?;
        Ok(())
    }
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("cmd")
            .args(["/c", "start", "", &url])
            .spawn()
            .map_err(|e| format!("Failed to open browser on Windows: {}", e))?;
        Ok(())
    }
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open")
            .arg(&url)
            .spawn()
            .map_err(|e| format!("Failed to open browser on Linux: {}", e))?;
        Ok(())
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
    {
        Err("Unsupported operating system for opening browser".to_string())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![core_base_url, core_health, open_browser_url])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
