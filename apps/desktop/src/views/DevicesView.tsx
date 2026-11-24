import { useEffect, useState } from "react";
import { api, Device, ActiveNode } from "../api";

export function DevicesView() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [activeNode, setActiveNode] = useState<ActiveNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hostHealth, setHostHealth] = useState<string>("Checking...");

  async function loadData() {
    setError(null);
    try {
      const [devList, nodeInfo, h] = await Promise.all([
        api.listDevices(),
        api.getActiveNode(),
        api.health().catch(() => ({ status: "down", service: "unknown" })),
      ]);
      setDevices(devList);
      setActiveNode(nodeInfo);
      setHostHealth(h.status === "ok" ? "ONLINE" : "UNREACHABLE");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="devices-view">
      <div className="view-toolbar">
        <div className="toolbar-left">
          <h2>Devices & Host Node</h2>
        </div>
        <div className="toolbar-right">
          <button className="btn-secondary" onClick={loadData}>
            🔄 Refresh Status
          </button>
        </div>
      </div>

      {error && <div className="error-banner">Error: {error}</div>}

      {/* Primary Mac Host Card */}
      <div className="card host-info-card">
        <div className="card-head-row">
          <div>
            <h3>Primary Authoritative Host</h3>
            <p className="dim text-sm">
              MacBook Core Engine holding the authoritative SQLite database.
            </p>
          </div>
          <span className={`badge ${hostHealth === "ONLINE" ? "badge-completed" : "badge-archived"}`}>
            {hostHealth}
          </span>
        </div>

        <div className="host-specs-grid">
          <div className="spec-item">
            <span className="spec-label">ACTIVE NODE ID</span>
            <span className="spec-value mono">{activeNode?.node_id || "mac-primary-01"}</span>
          </div>

          <div className="spec-item">
            <span className="spec-label">AUTHORITATIVE DATABASE</span>
            <span className="spec-value mono">SQLite · ~/.nexus/nexus.db</span>
          </div>

          <div className="spec-item">
            <span className="spec-label">CURRENT API BASE</span>
            <span className="spec-value mono">{api.getBaseUrl()}</span>
          </div>

          <div className="spec-item">
            <span className="spec-label">LAN DISCOVERY URL</span>
            <span className="spec-value mono">{activeNode?.lan_url || "http://127.0.0.1:8000"}</span>
          </div>

          <div className="spec-item" style={{ gridColumn: "span 2" }}>
            <span className="spec-label">ENCRYPTED RELAY PROXY</span>
            <span className="spec-value mono">
              {activeNode?.relay_proxy_url || "https://nexus-control-plane-uvi8.onrender.com/api/relay/proxy"}
            </span>
          </div>
        </div>
      </div>

      {/* Companion Devices */}
      <div className="card" style={{ marginTop: "20px" }}>
        <div className="card-head-row">
          <div>
            <h3>Connected Companion Clients ({devices.length})</h3>
            <p className="dim text-sm">
              Mobile, desktop, and CLI clients authenticated to your sovereign command center.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="loading-state">Loading registered devices...</div>
        ) : devices.length === 0 ? (
          <div className="empty-state">No external companion devices registered yet.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Device Name</th>
                <th style={{ width: "120px" }}>Platform</th>
                <th style={{ width: "120px" }}>Status</th>
                <th>Capabilities</th>
                <th style={{ width: "160px" }}>Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((d) => (
                <tr key={d.id}>
                  <td>
                    <span className="device-icon">
                      {d.platform.toLowerCase().includes("android") || d.platform.toLowerCase().includes("ios")
                        ? "📱"
                        : d.platform.toLowerCase().includes("cli")
                        ? "💻"
                        : "🖥️"}
                    </span>
                    <strong>{d.name}</strong>
                  </td>
                  <td>
                    <span className="badge badge-platform">{d.platform}</span>
                  </td>
                  <td>
                    <span className={`badge ${d.is_online ? "badge-completed" : "badge-archived"}`}>
                      {d.is_online ? "● Online" : "○ Offline"}
                    </span>
                  </td>
                  <td className="dim text-sm">{d.capabilities?.join(", ") || "full-access"}</td>
                  <td className="dim text-sm">
                    {d.last_seen ? new Date(d.last_seen).toLocaleString() : "Active"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Mobile Pairing & Federation Instructions */}
      <div className="card pairing-instructions-card" style={{ marginTop: "20px" }}>
        <h3>Mobile Companion Pairing & Sync</h3>
        <div className="steps-flow">
          <div className="step-box">
            <div className="step-num">1</div>
            <div className="step-content">
              <strong>Google Single Sign-On</strong>
              <p>Launch NEXUS Mobile on Android and tap "Continue with Google".</p>
            </div>
          </div>

          <div className="step-arrow">→</div>

          <div className="step-box">
            <div className="step-num">2</div>
            <div className="step-content">
              <strong>Automatic Discovery</strong>
              <p>Mobile locates this Mac host automatically over LAN or the encrypted cloud relay.</p>
            </div>
          </div>

          <div className="step-arrow">→</div>

          <div className="step-box">
            <div className="step-num">3</div>
            <div className="step-content">
              <strong>Zero-Config Sync</strong>
              <p>All projects, notes, and tasks sync directly with the Mac's SQLite database.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
