import { useEffect, useState } from "react";
import { api, User } from "../api";

interface Props {
  onLogout: () => void;
}

export function SettingsView({ onLogout }: Props) {
  const [user, setUser] = useState<User | null>(null);
  const [, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [customHostUrl, setCustomHostUrl] = useState(api.getBaseUrl());
  const [hostTestResult, setHostTestResult] = useState<string | null>(null);
  const [hostTesting, setHostTesting] = useState(false);

  const [storageRoots, setStorageRoots] = useState<string[]>([]);
  const [showToken, setShowToken] = useState(false);

  async function loadData() {
    setError(null);
    try {
      const [u, r] = await Promise.all([
        api.me().catch(() => null),
        api.listRoots().catch(() => []),
      ]);
      setUser(u);
      setStorageRoots(r);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function testHost(url: string) {
    setHostTesting(true);
    setHostTestResult(null);
    const start = performance.now();
    try {
      const res = await api.health(url);
      const ms = Math.round(performance.now() - start);
      setHostTestResult(`OK (${res.status}, ${ms}ms)`);
    } catch (err) {
      setHostTestResult(`Failed: ${String(err)}`);
    } finally {
      setHostTesting(false);
    }
  }

  function applyHostUrl(url: string) {
    api.setBaseUrl(url);
    setCustomHostUrl(url);
    testHost(url);
  }

  return (
    <div className="settings-view">
      <div className="view-toolbar">
        <div className="toolbar-left">
          <h2>Settings & Configuration</h2>
        </div>
      </div>

      {error && <div className="error-banner">Error: {error}</div>}

      <div className="settings-grid">
        {/* User Identity Profile */}
        <div className="card">
          <h3>Sovereign Identity</h3>
          <p className="dim text-sm">Authenticated via Google OAuth Single Sign-On.</p>

          <div className="setting-rows">
            <div className="setting-row">
              <span className="setting-label">ACCOUNT EMAIL</span>
              <span className="setting-value mono">{user?.email || "Authenticated Operator"}</span>
            </div>

            <div className="setting-row">
              <span className="setting-label">ACCOUNT ID</span>
              <span className="setting-value mono">#{user?.id ?? "1"}</span>
            </div>

            <div className="setting-row">
              <span className="setting-label">SESSION TOKEN</span>
              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <span className="setting-value mono text-xs">
                  {showToken ? api.getToken() : "••••••••••••••••••••••••••••••••••••••••"}
                </span>
                <button
                  className="btn-action"
                  onClick={() => setShowToken(!showToken)}
                >
                  {showToken ? "Hide" : "Show"}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Host Connection Endpoint Configuration */}
        <div className="card">
          <h3>Host Endpoint Routing</h3>
          <p className="dim text-sm">
            Select the authoritative Core API instance for projects, notes, and tasks.
          </p>

          <div className="preset-buttons">
            <button
              className={`preset-btn ${customHostUrl === api.getLocalBaseUrl() ? "active" : ""}`}
              onClick={() => applyHostUrl(api.getLocalBaseUrl())}
            >
              🖥️ Local Mac Host (127.0.0.1:8000)
            </button>
            <button
              className={`preset-btn ${customHostUrl === api.getCloudBaseUrl() ? "active" : ""}`}
              onClick={() => applyHostUrl(api.getCloudBaseUrl())}
            >
              ☁️ Cloud Control Plane / Relay
            </button>
          </div>

          <div style={{ marginTop: "16px" }}>
            <label className="dim text-xs">ACTIVE ENDPOINT URL</label>
            <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
              <input
                type="text"
                className="mono"
                value={customHostUrl}
                onChange={(e) => setCustomHostUrl(e.target.value)}
                placeholder="http://127.0.0.1:8000"
                style={{ flex: 1 }}
              />
              <button
                className="btn-secondary"
                disabled={hostTesting}
                onClick={() => testHost(customHostUrl)}
              >
                {hostTesting ? "Pinging..." : "Test"}
              </button>
              <button
                className="btn-primary"
                onClick={() => applyHostUrl(customHostUrl)}
              >
                Apply
              </button>
            </div>
            {hostTestResult && (
              <div
                className="dim text-sm"
                style={{
                  marginTop: "6px",
                  color: hostTestResult.startsWith("OK") ? "#10b981" : "#ef4444",
                }}
              >
                {hostTestResult}
              </div>
            )}
          </div>
        </div>

        {/* Jailed File System Roots */}
        <div className="card">
          <h3>Jailed Storage Roots</h3>
          <p className="dim text-sm">
            Files accessed or browsed by companion clients are strictly quarantined to these roots.
          </p>
          <ul className="roots-list">
            {storageRoots.length === 0 ? (
              <li className="dim mono text-sm">~/Documents (Default)</li>
            ) : (
              storageRoots.map((r, i) => (
                <li key={i} className="mono text-sm">
                  🔒 {r}
                </li>
              ))
            )}
          </ul>
        </div>

        {/* Software Release & System Info */}
        <div className="card">
          <h3>Build & Runtime Information</h3>
          <div className="setting-rows">
            <div className="setting-row">
              <span className="setting-label">APPLICATION</span>
              <span className="setting-value">NEXUS Desktop for macOS</span>
            </div>
            <div className="setting-row">
              <span className="setting-label">RELEASE VERSION</span>
              <span className="setting-value mono">0.1.0-alpha (Universal DMG)</span>
            </div>
            <div className="setting-row">
              <span className="setting-label">CORE SHELL</span>
              <span className="setting-value mono">Tauri 2 + React 18</span>
            </div>
            <div className="setting-row">
              <span className="setting-label">SECURITY POSTURE</span>
              <span className="setting-value">Ed25519 node identities · Local-first</span>
            </div>
          </div>
        </div>
      </div>

      {/* Disconnect / Logout */}
      <div className="logout-bar card" style={{ marginTop: "24px" }}>
        <div>
          <strong>Sign Out of NEXUS Command Center</strong>
          <p className="dim text-sm">
            Clears the local session token. The host service and local SQLite database will remain intact.
          </p>
        </div>
        <button
          className="btn-delete"
          style={{ padding: "10px 20px" }}
          onClick={() => {
            if (confirm("Sign out of this session?")) {
              api.clearToken();
              onLogout();
            }
          }}
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
