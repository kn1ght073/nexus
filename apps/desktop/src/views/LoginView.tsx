import React, { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { api, HostMode } from "../api";

async function tauriInvoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  try {
    return await invoke<T>(cmd, args);
  } catch (err) {
    if (typeof (window as any).__TAURI_INTERNALS__?.invoke === "function") {
      return await (window as any).__TAURI_INTERNALS__.invoke(cmd, args);
    }
    if (typeof (window as any).__TAURI__?.core?.invoke === "function") {
      return await (window as any).__TAURI__.core.invoke(cmd, args);
    }
    throw err;
  }
}

async function openExternalBrowser(url: string): Promise<void> {
  try {
    await tauriInvoke("open_browser_url", { url });
    return;
  } catch {
    // Web browser fallback
  }
  window.open(url, "_blank");
}

export function LoginView({ onLogin }: { onLogin: () => void }) {
  const [tokenInput, setTokenInput] = useState("");
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [activeBase, setActiveBase] = useState<string>(api.getBaseUrl());
  const [localHealth, setLocalHealth] = useState<"checking" | "online" | "offline">("checking");
  const [cloudHealth, setCloudHealth] = useState<"checking" | "online" | "offline">("checking");

  const checkHealth = () => {
    setLocalHealth("checking");
    setCloudHealth("checking");

    api.health(api.getLocalBaseUrl(), 2500)
      .then(() => setLocalHealth("online"))
      .catch(() => setLocalHealth("offline"));

    api.health(api.getCloudBaseUrl(), 4000)
      .then(() => setCloudHealth("online"))
      .catch(() => setCloudHealth("offline"));
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const selectEndpoint = (url: string) => {
    api.setBaseUrl(url);
    setActiveBase(api.getBaseUrl());
    setError(null);
  };

  async function handleGoogleLogin() {
    setError(null);
    setStatusMsg(null);
    let port: number | null = null;

    try {
      port = await tauriInvoke<number>("start_google_oauth_listener");
    } catch {
      port = null;
    }

    const baseStart = `${api.getCloudBaseUrl()}/api/auth/google/start`;
    const googleStartUrl = port ? `${baseStart}?cli_port=${port}` : baseStart;

    try {
      await openExternalBrowser(googleStartUrl);
      setShowTokenInput(true);
      if (port) {
        setStatusMsg("Browser opened for Google Sign-In. Waiting for automatic completion (or paste token below)...");
        const deadline = Date.now() + 180_000;
        const pollTimer = setInterval(async () => {
          if (Date.now() > deadline) {
            clearInterval(pollTimer);
            setStatusMsg(null);
            return;
          }
          try {
            const res = await tauriInvoke<{ completed: boolean; token?: string; refresh?: string }>("poll_oauth_result");
            if (res.completed && res.token) {
              clearInterval(pollTimer);
              setBusy(true);
              setStatusMsg("Google OAuth captured! Connecting to Mac Host...");
              try {
                await api.loginWithToken(res.token);
                onLogin();
              } catch (loginErr) {
                setError(loginErr instanceof Error ? loginErr.message : String(loginErr));
              } finally {
                setBusy(false);
                setStatusMsg(null);
              }
            }
          } catch {
            clearInterval(pollTimer);
          }
        }, 1000);
      }
    } catch (err) {
      setError(String(err));
    }
  }

  async function submitToken(e: React.FormEvent) {
    e.preventDefault();
    if (!tokenInput.trim()) return;
    setError(null);
    setBusy(true);
    try {
      await api.loginWithToken(tokenInput.trim());
      setActiveBase(api.getBaseUrl());
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid session token or host unreachable. Check the token and try again.");
    } finally {
      setBusy(false);
    }
  }

  const isLocalActive = api.isLocalUrl(activeBase);
  const isCloudActive = api.isCloudUrl(activeBase);

  return (
    <div className="login-wrap">
      <div className="login-card card">
        <div className="login-header">
          <div className="login-logo">⬡</div>
          <h1>NEXUS</h1>
          <p className="subtitle">Personal Sovereign Digital Infrastructure</p>
        </div>

        <div className="endpoint-toggle-container">
          <div className="endpoint-toggle-label">Select Auth / Host Endpoint</div>
          <div className="endpoint-toggle-buttons">
            <button
              type="button"
              className={`endpoint-btn ${isLocalActive ? "active" : ""}`}
              onClick={() => selectEndpoint(api.getLocalBaseUrl())}
            >
              <span className="endpoint-name">🖥️ Local Mac Host</span>
              <span className="endpoint-status">
                <span className={`status-dot ${localHealth}`} />
                <span>{localHealth === "online" ? "Online (:8000)" : localHealth === "checking" ? "Probing..." : "Offline"}</span>
              </span>
            </button>

            <button
              type="button"
              className={`endpoint-btn ${isCloudActive ? "active" : ""}`}
              onClick={() => selectEndpoint(api.getCloudBaseUrl())}
            >
              <span className="endpoint-name">☁️ Cloud Control Plane</span>
              <span className="endpoint-status">
                <span className={`status-dot ${cloudHealth}`} />
                <span>{cloudHealth === "online" ? "Online (Render)" : cloudHealth === "checking" ? "Probing..." : "Offline"}</span>
              </span>
            </button>
          </div>
        </div>

        <div className="host-badge-pill">
          <span className={`status-dot ${isLocalActive ? localHealth : cloudHealth}`} />
          <span className="mono text-xs">
            Auth: {isLocalActive ? "Local Host (127.0.0.1:8000)" : "Cloud Control Plane (onrender.com)"}
          </span>
        </div>

        <div className="login-body">
          <p className="login-desc">
            Identity and device federation are secured via Google OAuth. Authenticate to connect this desktop interface to your primary Mac host.
          </p>

          <button
            type="button"
            className="btn-google"
            disabled={busy}
            onClick={handleGoogleLogin}
          >
            <span className="google-icon">G</span>
            <span>Continue with Google</span>
          </button>
        </div>

        {statusMsg && <div className="info-banner">{statusMsg}</div>}
        {error && <div className="error-banner">{error}</div>}

        <div className="token-divider">
          <span>OR AUTHENTICATE WITH TOKEN</span>
        </div>

        <div className="token-section">
          {!showTokenInput ? (
            <button
              type="button"
              className="linklike"
              onClick={() => setShowTokenInput(true)}
            >
              Enter session token from CLI / Web →
            </button>
          ) : (
            <form onSubmit={submitToken} className="token-form">
              <label className="dim text-xs">JWT SESSION TOKEN (Auto-resolves Mac Host)</label>
              <input
                type="password"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="eyJhbGciOiJIUzI1NiIsIn..."
                required
              />
              <button type="submit" className="btn-primary" disabled={busy}>
                {busy ? "Verifying Session..." : "Authorize Session"}
              </button>
            </form>
          )}
        </div>

        <div className="login-foot">
          <span className="dim text-xs">Authoritative Database: Local SQLite on Mac</span>
        </div>
      </div>
    </div>
  );
}

export function CoreStatus({ hostMode, onRefresh }: { hostMode?: HostMode; onRefresh?: () => void }) {
  const mode = hostMode ?? api.getHostMode();
  const online = mode === "local" || mode === "lan" || mode === "relay";
  const label =
    mode === "local"
      ? "Mac Host: Local"
      : mode === "lan"
      ? "Mac Host: LAN"
      : mode === "relay"
      ? "Mac Host: Relay"
      : "Mac Host: Offline";

  return (
    <div
      className="core-status"
      style={{ cursor: onRefresh ? "pointer" : "default" }}
      onClick={onRefresh}
      title={api.getHostUrl() || "Click to re-discover Mac Host"}
    >
      <span className={`status-dot ${online ? "online" : "offline"}`} />
      <span className="text-xs dim">{label}</span>
    </div>
  );
}
