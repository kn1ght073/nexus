import React, { useEffect, useState } from "react";
import { api } from "../api";

export function LoginView({ onLogin }: { onLogin: () => void }) {
  const [tokenInput, setTokenInput] = useState("");
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleGoogleLogin() {
    setError(null);
    const googleStartUrl = `${api.baseUrl}/api/auth/google/start`;
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
      setError("Invalid session token or control plane unreachable.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <h1>NEXUS</h1>
        <p className="subtitle">Personal Digital Infrastructure — Sovereign & Hardened</p>

        <div style={{ margin: "16px 0", textAlign: "center" }}>
          <p style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "16px" }}>
            Identity registration & authentication are strictly managed via <b>Google OAuth</b>.
          </p>

          <button
            type="button"
            onClick={handleGoogleLogin}
            style={{
              width: "100%",
              padding: "10px",
              background: "#0284c7",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontWeight: 600,
              cursor: "pointer",
              marginBottom: "12px",
            }}
          >
            Sign in with Google OAuth
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        <div style={{ borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "14px", marginTop: "12px" }}>
          <button
            type="button"
            className="linklike"
            onClick={() => setShowTokenInput(!showTokenInput)}
            style={{ display: "block", width: "100%", textAlign: "center", marginBottom: "10px" }}
          >
            {showTokenInput ? "Hide session token input" : "Or enter session token from Web / CLI"}
          </button>

          {showTokenInput && (
            <form onSubmit={submitToken}>
              <label>
                Session Token
                <input
                  type="password"
                  value={tokenInput}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTokenInput(e.target.value)}
                  placeholder="eyJhbGciOiJIUzI1NiIsIn..."
                  required
                />
              </label>

              <button type="submit" disabled={busy} style={{ width: "100%", marginTop: "8px" }}>
                {busy ? "Verifying…" : "Authenticate with Token"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

export function CoreStatus() {
  const [health, setHealth] = useState<string>("checking…");
  useEffect(() => {
    api
      .health()
      .then((h) => setHealth(`${h.service} — ${h.status}`))
      .catch((e) => setHealth(`Control plane unreachable at ${api.baseUrl} (${String(e)})`));
  }, []);
  return <div className="core-status">Control Plane: {health}</div>;
}
