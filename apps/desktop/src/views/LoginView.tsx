import React, { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { api } from "../api";

async function openExternalBrowser(url: string): Promise<void> {
  // 1. Try official Tauri 2 invoke via @tauri-apps/api/core
  try {
    await invoke("open_browser_url", { url });
    return;
  } catch (err) {
    console.warn("invoke('open_browser_url') via @tauri-apps/api/core failed:", err);
  }

  // 2. Try window.__TAURI_INTERNALS__.invoke
  if (typeof (window as any).__TAURI_INTERNALS__?.invoke === "function") {
    try {
      await (window as any).__TAURI_INTERNALS__.invoke("open_browser_url", { url });
      return;
    } catch (err) {
      console.warn("invoke('open_browser_url') via __TAURI_INTERNALS__ failed:", err);
    }
  }

  // 3. Try window.__TAURI__.core.invoke
  if (typeof (window as any).__TAURI__?.core?.invoke === "function") {
    try {
      await (window as any).__TAURI__.core.invoke("open_browser_url", { url });
      return;
    } catch (err) {
      console.warn("invoke('open_browser_url') via __TAURI__.core failed:", err);
    }
  }

  // 4. Web browser fallback
  try {
    window.open(url, "_blank");
  } catch (err) {
    console.error("window.open fallback failed:", err);
  }
}

export function LoginView({ onLogin }: { onLogin: () => void }) {
  const [tokenInput, setTokenInput] = useState("");
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [activeBase, setActiveBase] = useState<string>(api.getBaseUrl());
  const [localHealth, setLocalHealth] = useState<"checking" | "online" | "offline">("checking");
  const [cloudHealth, setCloudHealth] = useState<"checking" | "online" | "offline">("checking");

  const checkHealth = () => {
    setLocalHealth("checking");
    setCloudHealth("checking");

    api.health(api.getLocalBaseUrl())
      .then(() => setLocalHealth("online"))
      .catch(() => setLocalHealth("offline"));

    api.health(api.getCloudBaseUrl())
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
    // Google OAuth always starts at Cloud Control Plane
    const googleStartUrl = `${api.getCloudBaseUrl()}/api/auth/google/start`;
    try {
      await openExternalBrowser(googleStartUrl);
      setShowTokenInput(true);
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
          <div className="endpoint-toggle-label">Select Host Endpoint</div>
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
            Active: {isLocalActive ? "Local Host (127.0.0.1:8000)" : "Cloud Relay (onrender.com)"}
          </span>
        </div>

        <div className="login-body">
          <p className="login-desc">
            Identity and device federation are secured via Google OAuth. Authenticate to connect this desktop interface to your primary Mac host.
          </p>

          <button
            type="button"
            className="btn-google"
            onClick={handleGoogleLogin}
          >
            <span className="google-icon">G</span>
            <span>Continue with Google</span>
          </button>
        </div>

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
              <label className="dim text-xs">JWT SESSION TOKEN (Auto-resolves Local & Cloud)</label>
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

export function CoreStatus() {
  const [health, setHealth] = useState<string>("Checking...");
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .health()
      .then((h) => {
        setHealth(`${h.service}`);
        setOnline(true);
      })
      .catch(() => {
        setHealth(`Offline`);
        setOnline(false);
      });
  }, []);

  return (
    <div className="core-status">
      <span className={`status-dot ${online ? "online" : "offline"}`} />
      <span className="text-xs dim">Host: {health}</span>
    </div>
  );
}
