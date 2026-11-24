import React, { useEffect, useState } from "react";
import { api } from "../api";

export function LoginView({ onLogin }: { onLogin: () => void }) {
  const [tokenInput, setTokenInput] = useState("");
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [hostStatus, setHostStatus] = useState<string>("Checking host...");

  useEffect(() => {
    api.health()
      .then((h) => setHostStatus(`Host Online (${h.service})`))
      .catch(() => setHostStatus(`Host offline or connecting to relay (${api.getBaseUrl()})`));
  }, []);

  async function handleGoogleLogin() {
    setError(null);
    const googleStartUrl = `${api.getBaseUrl()}/api/auth/google/start`;
    try {
      if ((window as any).__TAURI__?.shell?.open) {
        await (window as any).__TAURI__.shell.open(googleStartUrl);
      } else {
        window.open(googleStartUrl, "_blank");
      }
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
      onLogin();
    } catch (err) {
      setError("Invalid session token or host unreachable. Check the token and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card card">
        <div className="login-header">
          <div className="login-logo">⬡</div>
          <h1>NEXUS</h1>
          <p className="subtitle">Personal Sovereign Digital Infrastructure</p>
        </div>

        <div className="host-badge-pill">
          <span className="status-dot online" />
          <span className="mono text-xs">{hostStatus}</span>
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
              <label className="dim text-xs">JWT SESSION TOKEN</label>
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
