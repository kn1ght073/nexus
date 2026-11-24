import { useState, useEffect } from "react";
import { api, User } from "./api";
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

  useEffect(() => {
    if (loggedIn) {
      api.me().then(setUser).catch(() => {
        // If token invalid, force login
        // api.clearToken();
        // setLoggedIn(false);
      });
    }
  }, [loggedIn]);

  if (!loggedIn) {
    return (
      <div className="app-shell">
        <LoginView onLogin={() => setLoggedIn(true)} />
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
          <CoreStatus />
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
              setLoggedIn(false);
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Main View Area */}
      <main className="app-content">
        {view === "dashboard" && <DashboardView onNavigate={(v) => setView(v as View)} />}
        {view === "projects" && <ProjectsView />}
        {view === "tasks" && <TasksView />}
        {view === "notes" && <NotesView />}
        {view === "files" && <FilesView />}
        {view === "devices" && <DevicesView />}
        {view === "settings" && <SettingsView onLogout={() => setLoggedIn(false)} />}
      </main>
    </div>
  );
}
