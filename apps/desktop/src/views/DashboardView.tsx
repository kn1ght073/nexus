import { useEffect, useState } from "react";
import { api, Task, Project, Device } from "../api";

interface Props {
  view: "dashboard" | "projects" | "tasks" | "devices" | "activity";
}

export function DashboardView({ view }: Props) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [activity, setActivity] = useState<Array<{ id: number; action: string; detail: string; created_at: string }>>([]);
  const [error, setError] = useState<string | null>(null);
  const [newTask, setNewTask] = useState("");

  async function refresh() {
    setError(null);
    try {
      if (view === "dashboard" || view === "tasks") setTasks(await api.listTasks());
      if (view === "dashboard" || view === "projects") setProjects(await api.listProjects());
      if (view === "devices") setDevices(await api.listDevices());
      if (view === "activity") setActivity(await api.activity());
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    refresh();
    // live updates: the Core pushes TASK_CREATED / PROJECT_UPDATED events
    const ws = new WebSocket(`ws://127.0.0.1:8000/ws`);
    ws.onopen = () => {
      const token = localStorage.getItem("nexus.token");
      if (token) ws.send(token);
    };
    ws.onmessage = () => refresh(); // any event for this user triggers a refetch
    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  async function addTask(e: React.FormEvent) {
    e.preventDefault();
    if (!newTask.trim()) return;
    await api.createTask(newTask.trim());
    setNewTask("");
    refresh();
  }

  if (error) return <div className="error">Failed to load: {error}</div>;

  if (view === "dashboard") {
    const pending = tasks.filter((t) => t.status !== "completed");
    return (
      <div className="grid">
        <section className="card">
          <h2>Today</h2>
          <div className="stat">{pending.length} open task(s)</div>
          <ul>
            {pending.slice(0, 5).map((t) => (
              <li key={t.id}>{t.title}</li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h2>Projects</h2>
          <div className="stat">{projects.length}</div>
          <ul>
            {projects.slice(0, 5).map((p) => (
              <li key={p.id}>
                {p.title} <span className="dim">({p.status})</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    );
  }

  if (view === "tasks") {
    return (
      <section className="card">
        <h2>Tasks</h2>
        <form onSubmit={addTask} className="row">
          <input
            placeholder="New task…"
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
          />
          <button type="submit">Add</button>
        </form>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Project</th>
              <th>Status</th>
              <th>Rev</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td>{t.id}</td>
                <td>{t.title}</td>
                <td>{t.project_id ?? "—"}</td>
                <td>
                  <span className={`badge ${t.status}`}>{t.status}</span>
                </td>
                <td>{t.revision}</td>
                <td>
                  {t.status !== "completed" && (
                    <button
                      onClick={async () => {
                        await api.completeTask(t.id);
                        refresh();
                      }}
                    >
                      Done
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  }

  if (view === "projects") {
    return (
      <section className="card">
        <h2>Projects</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Status</th>
              <th>Rev</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.title}</td>
                <td>
                  <span className={`badge ${p.status}`}>{p.status}</span>
                </td>
                <td>{p.revision}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  }

  if (view === "devices") {
    return (
      <section className="card">
        <h2>Devices</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Platform</th>
              <th>Online</th>
              <th>Capabilities</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((d) => (
              <tr key={d.id}>
                <td>{d.name}</td>
                <td>{d.platform}</td>
                <td>{d.is_online ? "● online" : "○ offline"}</td>
                <td>{d.capabilities.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  }

  return (
    <section className="card">
      <h2>Activity</h2>
      <ul className="activity">
        {activity.map((a) => (
          <li key={a.id}>
            <span className="dim">{new Date(a.created_at).toLocaleTimeString()}</span>{" "}
            <strong>{a.action}</strong> <span className="dim">{a.detail}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
