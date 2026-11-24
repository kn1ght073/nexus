import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { api, User } from "../api";

interface Props {
  onLogout: () => void;
  onHostChanged?: () => void;
}

export function SettingsView({ onLogout, onHostChanged }: Props) {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [customHostUrl, setCustomHostUrl] = useState(api.getHostUrl() || api.getLocalBaseUrl());
  const [hostTestResult, setHostTestResult] = useState<string | null>(null);
  const [hostTesting, setHostTesting] = useState(false);

  const [storageRoots, setStorageRoots] = useState<string[]>([]);
  const [showToken, setShowToken] = useState(false);
  const [daemonMsg, setDaemonMsg] = useState<string | null>(null);

  async function loadData() {
    setError(null);
    try {
      const [u, r] = await Promise.all([
        api.me().catch(() => null),
        api.listRoots().catch(() => []),
      ]);
      setUser(u);
      setStorageRoots(r);
      if (api.getHostUrl()) {
        setCustomHostUrl(api.getHostUrl());
      }
    } catch (err) {
      setError(String(err));
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
      setHostTestResult(`OK (${res.service}, mode=${res.mode ?? "node"}, ${ms}ms)`);
    } catch (err) {
      setHostTestResult(`Failed: ${String(err)}`);
    } finally {
      setHostTesting(false);
    }
  }

  async function applyHostUrl(url: string) {
    api.setBaseUrl(url);
    setCustomHostUrl(url);
    await api.resolveHost();
    await testHost(url);
    onHostChanged?.();
  }

  async function handleStartDaemon() {
    setDaemonMsg("Starting local Mac host...");
    try {
      const msg = await invoke<string>("start_host_daemon");
      setDaemonMsg(msg);
      setTimeout(async () => {
        await api.resolveHost();
        onHostChanged?.();
        loadData();
      }, 1800);
    } catch (err) {
      setDaemonMsg(`Start failed: ${String(err)}`);
    }
  }

  async function handleStopDaemon() {
    try {
      const msg = await invoke<string>("stop_host_daemon");
      setDaemonMsg(msg);
      await api.resolveHost();
      onHostChanged?.();
    } catch (err) {
      setDaemonMsg(`Stop failed: ${String(err)}`);
    }
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
              <span className="setting-label">ACTIVE HOST MODE</span>
              <span className="setting-value mono">{api.getHostMode().toUpperCase()}</span>
            </div>

            <div className="setting-row">
              <span className="setting-label">SESSION TOKEN</span>
              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <span className="setting-value mono text-xs">
                  {showToken ? (api.getHostToken() || api.getToken()) : "••••••••••••••••••••••••••••••••••••••••"}
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
          <h3>Mac Host Lifecycle & Routing</h3>
          <p className="dim text-sm">
            Authoritative personal records live on your Mac Host. Control Plane handles identity & relay discovery.
          </p>

          <div className="preset-buttons">
            <button
              className={`preset-btn ${api.getHostMode() === "local" ? "active" : ""}`}
              onClick={() => applyHostUrl(api.getLocalBaseUrl())}
            >
              🖥️ Local Mac Host (127.0.0.1:8000)
            </button>
            <button
              className={`preset-btn ${api.getHostMode() === "relay" ? "active" : ""}`}
              onClick={() => applyHostUrl(api.getCloudBaseUrl())}
            >
              ☁️ Auto-Discover via Control Plane
            </button>
          </div>

          <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
            <button className="btn-primary" onClick={handleStartDaemon}>
              Start Local Host
            </button>
            <button className="btn-secondary" onClick={handleStopDaemon}>
              Stop Local Host
            </button>
          </div>
          {daemonMsg && <div className="dim text-xs" style={{ marginTop: "8px" }}>{daemonMsg}</div>}

          <div style={{ marginTop: "16px" }}>
            <label className="dim text-xs">CUSTOM HOST ENDPOINT URL</label>
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
              <li className="dim mono text-sm">~/Documents (Connect to Mac Host to list active roots)</li>
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
              <span className="setting-value mono">0.1.0 (macOS Release)</span>
            </div>
            <div className="setting-row">
              <span className="setting-label">CORE SHELL</span>
              <span className="setting-value mono">Tauri 2 + React 18</span>
            </div>
            <div className="setting-row">
              <span className="setting-label">AUTHORITATIVE HOST</span>
              <span className="setting-value mono">{api.getHostUrl() || "Offline"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Disconnect / Logout */}
      <div className="logout-bar card" style={{ marginTop: "24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
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
