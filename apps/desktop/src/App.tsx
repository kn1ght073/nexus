import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { api, User, HostMode } from "./api";
import { LoginView, CoreStatus } from "./views/LoginView";
import { DashboardView } from "./views/DashboardView";
import { ProjectsView } from "./views/ProjectsView";
import { TasksView } from "./views/TasksView";
import { NotesView } from "./views/NotesView";
import { FilesView } from "./views/FilesView";
import { DevicesView } from "./views/DevicesView";
import { SettingsView } from "./views/SettingsView";

export type View = "dashboard" | "projects" | "tasks" | "notes" | "files" | "devices" | "settings";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(api.hasToken());
  const [view, setView] = useState<View>("dashboard");
  const [user, setUser] = useState<User | null>(null);
  const [hostMode, setHostMode] = useState<HostMode>(api.getHostMode());
  const [startingHost, setStartingHost] = useState(false);
  const [hostBannerMsg, setHostBannerMsg] = useState<string | null>(null);

  async function refreshConnection() {
    if (!api.hasToken()) return;
    api.me().then(setUser).catch(() => {});
    const resolved = await api.resolveHost();
    setHostMode(resolved.mode);
  }

  useEffect(() => {
    if (loggedIn) {
      refreshConnection();
    }
  }, [loggedIn]);

  async function handleStartLocalHost() {
    setStartingHost(true);
    setHostBannerMsg(null);
    try {
      let startedMsg = "";
      try {
        startedMsg = await invoke<string>("start_host_daemon");
      } catch (e) {
        if (typeof (window as any).__TAURI_INTERNALS__?.invoke === "function") {
          startedMsg = await (window as any).__TAURI_INTERNALS__.invoke("start_host_daemon");
        } else {
          throw e;
        }
      }
      setHostBannerMsg(`${startedMsg}. Waiting for port 8000...`);
      for (let i = 0; i < 12; i++) {
        await new Promise((r) => setTimeout(r, 700));
        const res = await api.resolveHost();
        if (res.mode !== "none") {
          setHostMode(res.mode);
          setHostBannerMsg(null);
          return;
        }
      }
      setHostBannerMsg("Host daemon did not respond on :8000 yet. Try 'Retry Discovery' or run `nexus host start`.");
    } catch (err) {
      setHostBannerMsg(String(err));
    } finally {
      setStartingHost(false);
    }
  }

  if (!loggedIn) {
    return (
      <div className="app-shell">
        <LoginView
          onLogin={() => {
            setHostMode(api.getHostMode());
            setLoggedIn(true);
          }}
        />
      </div>
    );
  }

  return (
    <div className="app-shell">
      {/* Top Application Bar */}
      <header className="app-header">
        <div className="header-left">
          <div className="brand-logo">⬡</div>
          <div className="brand-title">NEXUS</div>
          <span className="brand-badge">SOVEREIGN</span>
          <CoreStatus hostMode={hostMode} onRefresh={refreshConnection} />
        </div>

        <nav className="header-nav">
          {(
            [
              { id: "dashboard", label: "Dashboard", icon: "📊" },
              { id: "projects", label: "Projects", icon: "📁" },
              { id: "tasks", label: "Tasks", icon: "✅" },
              { id: "notes", label: "Notes", icon: "📝" },
              { id: "files", label: "Files", icon: "📦" },
              { id: "devices", label: "Devices", icon: "📱" },
              { id: "settings", label: "Settings", icon: "⚙️" },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              className={`nav-tab ${view === tab.id ? "active" : ""}`}
              onClick={() => setView(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>

        <div className="header-right">
          {user && (
            <div className="user-pill" title={user.email}>
              <span className="user-dot">●</span>
              <span className="user-email">{user.email}</span>
            </div>
          )}
          <button
            className="btn-logout"
            onClick={() => {
              api.clearToken();
              setHostMode("none");
              setLoggedIn(false);
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Host Offline Recovery Banner */}
      {hostMode === "none" && (
        <div className="host-offline-banner">
          <div>
            <strong>Mac Host Node Offline:</strong> Connected to Control Plane for identity only. Start your Mac Host to access Projects, Tasks, Notes, and Shared Files.
            {hostBannerMsg && <div className="text-xs dim" style={{ marginTop: "4px" }}>{hostBannerMsg}</div>}
          </div>
          <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
            <button className="btn-primary" disabled={startingHost} onClick={handleStartLocalHost}>
              {startingHost ? "Starting Host..." : "Start Local Mac Host"}
            </button>
            <button className="btn-secondary" onClick={refreshConnection}>
              Retry Discovery
            </button>
          </div>
        </div>
      )}

      {/* Main View Area */}
      <main className="app-content">
        {view === "dashboard" && <DashboardView onNavigate={(v) => setView(v as View)} />}
        {view === "projects" && <ProjectsView />}
        {view === "tasks" && <TasksView />}
        {view === "notes" && <NotesView />}
        {view === "files" && <FilesView />}
        {view === "devices" && <DevicesView />}
        {view === "settings" && (
          <SettingsView
            onLogout={() => {
              setHostMode("none");
              setLoggedIn(false);
            }}
            onHostChanged={refreshConnection}
          />
        )}
      </main>
    </div>
  );
}
