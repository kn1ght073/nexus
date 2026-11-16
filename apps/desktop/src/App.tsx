import { useState } from "react";
import { api } from "../api";
import { LoginView, CoreStatus } from "./views/LoginView";
import { DashboardView } from "./views/DashboardView";

type View = "dashboard" | "projects" | "tasks" | "devices" | "activity";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(api.hasToken());
  const [view, setView] = useState<View>("dashboard");

  if (!loggedIn) {
    return (
      <div className="app">
        <CoreStatus />
        <LoginView onLogin={() => setLoggedIn(true)} />
      </div>
    );
  }

  return (
    <div className="app">
      <header>
        <h1>NEXUS</h1>
        <CoreStatus />
        <button
          className="linklike"
          onClick={() => {
            api.clearToken();
            setLoggedIn(false);
          }}
        >
          Log out
        </button>
      </header>
      <nav>
        {(["dashboard", "projects", "tasks", "devices", "activity"] as View[]).map((v) => (
          <button key={v} className={view === v ? "active" : ""} onClick={() => setView(v)}>
            {v}
          </button>
        ))}
      </nav>
      <main>
        <DashboardView view={view} />
      </main>
    </div>
  );
}
