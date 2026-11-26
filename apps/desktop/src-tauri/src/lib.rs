//! NEXUS Desktop — Tauri 2 shell.
//!
//! Provides native OS integration:
//! - `open_browser_url`: opens OAuth URLs in the user's default system browser
//! - `start_google_oauth_listener` / `poll_oauth_result`: loopback callback capture
//! - `get_host_daemon_status` / `start_host_daemon` / `stop_host_daemon`: local Mac host lifecycle

use serde::Serialize;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

#[derive(Serialize)]
pub struct HealthStatus {
    pub ok: bool,
    pub detail: String,
}

#[derive(Clone, Serialize, Default)]
pub struct OAuthResult {
    pub completed: bool,
    pub token: Option<String>,
    pub refresh: Option<String>,
}

struct OAuthState {
    result: Arc<Mutex<OAuthResult>>,
}

const CORE_URL: &str = "https://nexus-control-plane-uvi8.onrender.com";

#[tauri::command]
fn core_base_url() -> String {
    CORE_URL.to_string()
}

#[tauri::command]
async fn core_health(base_url: Option<String>) -> HealthStatus {
    use std::net::{SocketAddr, TcpStream};
    use std::time::Duration;

    let target = base_url.unwrap_or_else(|| "http://127.0.0.1:8000".to_string());
    if target.contains("127.0.0.1:8000") || target.contains("localhost:8000") {
        let addr: SocketAddr = ([127, 0, 0, 1], 8000).into();
        match TcpStream::connect_timeout(&addr, Duration::from_millis(1000)) {
            Ok(_) => HealthStatus {
                ok: true,
                detail: "Local Mac Host is online on port 8000".to_string(),
            },
            Err(e) => HealthStatus {
                ok: false,
                detail: format!("Port 8000 unreachable: {}", e),
            },
        }
    } else {
        HealthStatus {
            ok: true,
            detail: format!("Target URL configured: {}", target),
        }
    }
}

#[tauri::command]
fn native_local_request(
    path: String,
    method: Option<String>,
    headers: Option<std::collections::HashMap<String, String>>,
    body: Option<String>,
) -> Result<serde_json::Value, String> {
    use std::io::{Read, Write};
    use std::net::{SocketAddr, TcpStream};
    use std::time::Duration;

    let method_str = method.unwrap_or_else(|| "GET".to_string()).to_uppercase();
    let addr: SocketAddr = ([127, 0, 0, 1], 8000).into();
    let mut stream = TcpStream::connect_timeout(&addr, Duration::from_millis(3000))
        .map_err(|e| format!("Host connection failed on port 8000: {}", e))?;
    let _ = stream.set_read_timeout(Some(Duration::from_millis(4000)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(4000)));

    let clean_path = if path.starts_with('/') { path } else { format!("/{}", path) };
    let req_body = body.unwrap_or_default();

    let mut req_str = format!("{} {} HTTP/1.0\r\nHost: 127.0.0.1:8000\r\nConnection: close\r\n", method_str, clean_path);
    if let Some(hdrs) = headers {
        for (k, v) in hdrs {
            req_str.push_str(&format!("{}: {}\r\n", k, v));
        }
    }
    if !req_body.is_empty() {
        req_str.push_str(&format!("Content-Length: {}\r\n", req_body.len()));
    }
    req_str.push_str("\r\n");
    req_str.push_str(&req_body);

    stream.write_all(req_str.as_bytes()).map_err(|e| e.to_string())?;

    let mut response_bytes = Vec::new();
    let _ = stream.read_to_end(&mut response_bytes);

    let resp_text = String::from_utf8_lossy(&response_bytes).to_string();
    let parts: Vec<&str> = resp_text.splitn(2, "\r\n\r\n").collect();
    if parts.is_empty() {
        return Err("Empty response from local host".to_string());
    }

    let header_part = parts[0];
    let body_part = if parts.len() > 1 { parts[1] } else { "" };

    let status_line = header_part.lines().next().unwrap_or("");
    let status_code: u16 = status_line
        .split_whitespace()
        .nth(1)
        .and_then(|s| s.parse().ok())
        .unwrap_or(500);

    let parsed_body: serde_json::Value = serde_json::from_str(body_part)
        .unwrap_or_else(|_| serde_json::Value::String(body_part.to_string()));

    if status_code >= 400 {
        return Err(format!("{}: {}", status_code, body_part));
    }

    Ok(parsed_body)
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

fn decode_url_param(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let bytes = s.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' && i + 2 < bytes.len() {
            if let Ok(hex) = std::str::from_utf8(&bytes[i + 1..i + 3]) {
                if let Ok(val) = u8::from_str_radix(hex, 16) {
                    out.push(val as char);
                    i += 3;
                    continue;
                }
            }
        } else if bytes[i] == b'+' {
            out.push(' ');
            i += 1;
            continue;
        }
        out.push(bytes[i] as char);
        i += 1;
    }
    out
}

#[tauri::command]
fn start_google_oauth_listener(state: tauri::State<'_, OAuthState>) -> Result<u16, String> {
    {
        let mut res = state.result.lock().map_err(|e| e.to_string())?;
        *res = OAuthResult::default();
    }

    let listener = TcpListener::bind("127.0.0.1:0").map_err(|e| e.to_string())?;
    let port = listener.local_addr().map_err(|e| e.to_string())?.port();
    let result_arc = Arc::clone(&state.result);

    std::thread::spawn(move || {
        listener.set_nonblocking(false).ok();
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(180);
        for stream_res in listener.incoming() {
            if std::time::Instant::now() > deadline {
                break;
            }
            if let Ok(mut stream) = stream_res {
                let mut buf = [0u8; 8192];
                let n = stream.read(&mut buf).unwrap_or(0);
                let req = String::from_utf8_lossy(&buf[..n]);
                let first_line = req.lines().next().unwrap_or("");

                if first_line.starts_with("OPTIONS ") {
                    let resp = "HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, OPTIONS\r\nAccess-Control-Allow-Headers: *\r\nContent-Length: 0\r\n\r\n";
                    let _ = stream.write_all(resp.as_bytes());
                    continue;
                }

                if let Some(path_part) = first_line.split_whitespace().nth(1) {
                    if let Some((_, qs)) = path_part.split_once('?') {
                        let mut tok: Option<String> = None;
                        let mut ref_tok: Option<String> = None;
                        for pair in qs.split('&') {
                            if let Some((k, v)) = pair.split_once('=') {
                                if k == "token" {
                                    tok = Some(decode_url_param(v));
                                } else if k == "refresh" {
                                    ref_tok = Some(decode_url_param(v));
                                }
                            }
                        }
                        if let Some(t) = tok {
                            if let Ok(mut guard) = result_arc.lock() {
                                guard.completed = true;
                                guard.token = Some(t);
                                guard.refresh = ref_tok;
                            }
                            let body = r#"{"status":"ok","message":"Desktop authorized"}"#;
                            let resp = format!(
                                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}",
                                body.len(),
                                body
                            );
                            let _ = stream.write_all(resp.as_bytes());
                            break;
                        }
                    }
                }
                let body = r#"{"status":"ignored"}"#;
                let resp = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {}\r\n\r\n{}",
                    body.len(),
                    body
                );
                let _ = stream.write_all(resp.as_bytes());
            }
        }
    });

    Ok(port)
}

#[tauri::command]
fn poll_oauth_result(state: tauri::State<'_, OAuthState>) -> Result<OAuthResult, String> {
    let res = state.result.lock().map_err(|e| e.to_string())?;
    Ok(res.clone())
}

fn resolve_binary(name: &str) -> Option<PathBuf> {
    let home = std::env::var("HOME").unwrap_or_default();
    let candidate_dirs = [
        "/opt/homebrew/bin".to_string(),
        "/usr/local/bin".to_string(),
        "/usr/bin".to_string(),
        format!("{}/.local/bin", home),
        format!("{}/Documents/AppDev/NEXUS/apps/cli/venv/bin", home),
        format!("{}/Documents/AppDev/NEXUS/services/core-api/.venv/bin", home),
    ];
    for dir in &candidate_dirs {
        let p = PathBuf::from(dir).join(name);
        if p.exists() && p.is_file() {
            return Some(p);
        }
    }
    None
}

fn is_pid_alive(pid: i32) -> bool {
    if pid <= 0 {
        return false;
    }
    std::process::Command::new("/bin/kill")
        .args(["-0", &pid.to_string()])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

#[tauri::command]
fn get_host_daemon_status() -> Result<serde_json::Value, String> {
    let home = std::env::var("HOME").map_err(|e| e.to_string())?;
    let pid_file = PathBuf::from(&home).join(".nexus").join("host.pid");
    let mut running = false;
    let mut pid_val: Option<i32> = None;

    if pid_file.exists() {
        if let Ok(content) = std::fs::read_to_string(&pid_file) {
            if let Ok(pid) = content.trim().parse::<i32>() {
                pid_val = Some(pid);
                running = is_pid_alive(pid);
            }
        }
    }

    Ok(serde_json::json!({
        "running": running,
        "pid": pid_val,
        "cli_available": resolve_binary("nexus").is_some(),
        "core_available": resolve_binary("uvicorn").is_some() || resolve_binary("nexus").is_some(),
    }))
}

#[tauri::command]
fn start_host_daemon() -> Result<String, String> {
    let home = std::env::var("HOME").map_err(|e| e.to_string())?;
    let path_env = format!(
        "/opt/homebrew/bin:/usr/local/bin:{}/.local/bin:{}",
        home,
        std::env::var("PATH").unwrap_or_default()
    );

    if let Some(nexus_bin) = resolve_binary("nexus") {
        std::process::Command::new(nexus_bin)
            .args(["host", "start", "--daemon"])
            .env("PATH", &path_env)
            .spawn()
            .map_err(|e| format!("Failed to start host via nexus CLI: {}", e))?;
        return Ok("Started local Mac host daemon via nexus CLI".to_string());
    }

    if let Some(uvicorn_bin) = resolve_binary("uvicorn") {
        let nexus_dir = PathBuf::from(&home).join(".nexus");
        std::fs::create_dir_all(&nexus_dir).map_err(|e| e.to_string())?;
        let core_dir = PathBuf::from(&home).join("Documents/AppDev/NEXUS/services/core-api");
        let db_path = nexus_dir.join("nexus.db");
        let mut cmd = std::process::Command::new(uvicorn_bin);
        cmd.args([
            "nexus_core.main:create_app",
            "--factory",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ])
        .env("NEXUS_CONTROL_PLANE_MODE", "false")
        .env("NEXUS_DATABASE_PATH", db_path.to_string_lossy().to_string())
        .env("PATH", &path_env);
        if core_dir.exists() {
            cmd.current_dir(core_dir);
        }
        let child = cmd.spawn().map_err(|e| format!("Failed to spawn uvicorn: {}", e))?;
        let _ = std::fs::write(nexus_dir.join("host.pid"), child.id().to_string());
        return Ok(format!("Started local Mac host daemon (PID {})", child.id()));
    }

    Err("NEXUS CLI / Core API runtime not found on this machine. Run `nexus host start` in terminal or connect to a remote Mac host.".to_string())
}

#[tauri::command]
fn stop_host_daemon() -> Result<String, String> {
    let home = std::env::var("HOME").map_err(|e| e.to_string())?;
    let pid_file = PathBuf::from(&home).join(".nexus").join("host.pid");
    if !pid_file.exists() {
        return Ok("No host daemon PID file found".to_string());
    }
    let content = std::fs::read_to_string(&pid_file).map_err(|e| e.to_string())?;
    let pid = content.trim().parse::<i32>().map_err(|e| e.to_string())?;
    let _ = std::process::Command::new("/bin/kill")
        .args(["-TERM", &pid.to_string()])
        .status();
    let _ = std::fs::remove_file(pid_file);
    Ok(format!("Sent SIGTERM to PID {}", pid))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(OAuthState {
            result: Arc::new(Mutex::new(OAuthResult::default())),
        })
        .invoke_handler(tauri::generate_handler![
            core_base_url,
            core_health,
            open_browser_url,
            start_google_oauth_listener,
            poll_oauth_result,
            get_host_daemon_status,
            start_host_daemon,
            stop_host_daemon,
            native_local_request
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
