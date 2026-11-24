import React, { useEffect, useState } from "react";
import { api, Project, Task, Note, Device, ActiveNode, ActivityItem } from "../api";

interface Props {
  onNavigate: (view: "projects" | "notes" | "tasks" | "files" | "devices" | "settings") => void;
}

export function DashboardView({ onNavigate }: Props) {
  const [, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hostHealthy, setHostHealthy] = useState<boolean | null>(null);
  const [hostLatency, setHostLatency] = useState<number | null>(null);
  const [, setActiveNode] = useState<ActiveNode | null>(null);

  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [filesCount, setFilesCount] = useState<number>(0);

  // Quick action modal state
  const [quickTaskModal, setQuickTaskModal] = useState(false);
  const [quickTaskTitle, setQuickTaskTitle] = useState("");
  const [quickProjectModal, setQuickProjectModal] = useState(false);
  const [quickProjectTitle, setQuickProjectTitle] = useState("");
  const [quickProjectDesc, setQuickProjectDesc] = useState("");

  async function refreshData() {
    setError(null);
    const start = performance.now();
    try {
      // 1. Probe current host endpoint
      try {
        await api.health();
        setHostHealthy(true);
        setHostLatency(Math.round(performance.now() - start));
      } catch {
        setHostHealthy(false);
        setHostLatency(null);
      }

      // 2. Load metrics in parallel
      const [projList, taskList, noteList, devList, actList, nodeInfo] = await Promise.all([
        api.listProjects().catch(() => []),
        api.listTasks().catch(() => []),
        api.listNotes().catch(() => []),
        api.listDevices().catch(() => []),
        api.activity(12).catch(() => []),
        api.getActiveNode().catch(() => null),
      ]);

      setProjects(projList);
      setTasks(taskList);
      setNotes(noteList);
      setDevices(devList);
      setActivity(actList);
      setActiveNode(nodeInfo);

      // Try counting files in default storage root
      try {
        const files = await api.browseFiles();
        setFilesCount(files.length);
      } catch {
        setFilesCount(0);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 15000);
    return () => clearInterval(interval);
  }, []);

  async function handleCreateQuickTask(e: React.FormEvent) {
    e.preventDefault();
    if (!quickTaskTitle.trim()) return;
    try {
      await api.createTask(quickTaskTitle.trim());
      setQuickTaskTitle("");
      setQuickTaskModal(false);
      refreshData();
    } catch (err) {
      alert(`Error adding task: ${err}`);
    }
  }

  async function handleCreateQuickProject(e: React.FormEvent) {
    e.preventDefault();
    if (!quickProjectTitle.trim()) return;
    try {
      await api.createProject(quickProjectTitle.trim(), quickProjectDesc.trim());
      setQuickProjectTitle("");
      setQuickProjectDesc("");
      setQuickProjectModal(false);
      refreshData();
    } catch (err) {
      alert(`Error creating project: ${err}`);
    }
  }

  const openTasks = tasks.filter((t) => t.status !== "completed");
  const completedTasks = tasks.filter((t) => t.status === "completed");
  const isLocalHost = api.getBaseUrl().includes("127.0.0.1") || api.getBaseUrl().includes("localhost");

  return (
    <div className="dashboard-view">
      {error && <div className="error-banner">Error: {error}</div>}
      {/* Host Status Banner */}
      <div className="host-banner card">
        <div className="host-banner-left">
          <div className="host-indicator">
            <span className={`status-dot ${hostHealthy ? "online" : "offline"}`} />
            <div>
              <div className="host-title">
                {isLocalHost ? "Local Mac Host (Primary Core)" : "Remote / Relay Host"}
              </div>
              <div className="host-subtitle">
                Endpoint: <code>{api.getBaseUrl()}</code>
                {hostLatency !== null && <span className="host-ping"> · {hostLatency}ms</span>}
              </div>
            </div>
          </div>
        </div>

        <div className="host-banner-right">
          <div className="db-badge">
            <span className="db-icon">🗄️</span>
            <div>
              <div className="db-label">Authoritative Storage</div>
              <div className="db-value">SQLite · ~/.nexus/nexus.db</div>
            </div>
          </div>
          <button className="btn-secondary" onClick={() => onNavigate("settings")}>
            Host Config
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="stats-grid">
        <div className="stat-card" onClick={() => onNavigate("projects")}>
          <div className="stat-header">
            <span className="stat-label">PROJECTS</span>
            <span className="stat-icon">📁</span>
          </div>
          <div className="stat-number">{projects.length}</div>
          <div className="stat-foot">
            {projects.filter((p) => p.status === "active").length} active projects
          </div>
        </div>

        <div className="stat-card" onClick={() => onNavigate("tasks")}>
          <div className="stat-header">
            <span className="stat-label">TASKS</span>
            <span className="stat-icon">✅</span>
          </div>
          <div className="stat-number">{openTasks.length}</div>
          <div className="stat-foot">{completedTasks.length} completed</div>
        </div>

        <div className="stat-card" onClick={() => onNavigate("notes")}>
          <div className="stat-header">
            <span className="stat-label">NOTES</span>
            <span className="stat-icon">📝</span>
          </div>
          <div className="stat-number">{notes.length}</div>
          <div className="stat-foot">Sovereign knowledge items</div>
        </div>

        <div className="stat-card" onClick={() => onNavigate("files")}>
          <div className="stat-header">
            <span className="stat-label">SHARED FILES</span>
            <span className="stat-icon">📦</span>
          </div>
          <div className="stat-number">{filesCount}</div>
          <div className="stat-foot">Jailed storage roots</div>
        </div>

        <div className="stat-card" onClick={() => onNavigate("devices")}>
          <div className="stat-header">
            <span className="stat-label">COMPANIONS</span>
            <span className="stat-icon">📱</span>
          </div>
          <div className="stat-number">{devices.length}</div>
          <div className="stat-foot">
            {devices.filter((d) => d.is_online).length} online now
          </div>
        </div>
      </div>

      {/* Action Bar */}
      <div className="actions-bar">
        <button className="btn-primary" onClick={() => setQuickProjectModal(true)}>
          + New Project
        </button>
        <button className="btn-primary" onClick={() => setQuickTaskModal(true)}>
          + Add Task
        </button>
        <button className="btn-secondary" onClick={() => onNavigate("notes")}>
          + Write Note
        </button>
        <button className="btn-secondary" onClick={() => onNavigate("files")}>
          Browse Files
        </button>
        <button className="btn-secondary" onClick={refreshData}>
          🔄 Refresh
        </button>
      </div>

      {/* Split Grid: Today's Tasks & Activity Log */}
      <div className="dashboard-columns">
        <section className="card col-main">
          <div className="section-header">
            <h3>Active Tasks</h3>
            <button className="linklike" onClick={() => onNavigate("tasks")}>
              View All →
            </button>
          </div>

          {openTasks.length === 0 ? (
            <div className="empty-state">No open tasks. Click "+ Add Task" to create one.</div>
          ) : (
            <div className="task-list">
              {openTasks.slice(0, 7).map((t) => (
                <div key={t.id} className="task-row">
                  <div className="task-info">
                    <span className="task-id">#{t.id}</span>
                    <span className="task-title">{t.title}</span>
                    {t.project_id && (
                      <span className="project-tag">
                        {projects.find((p) => p.id === t.project_id)?.title ?? `Proj #${t.project_id}`}
                      </span>
                    )}
                  </div>
                  <button
                    className="btn-done"
                    onClick={async () => {
                      await api.completeTask(t.id);
                      refreshData();
                    }}
                  >
                    Done
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="card col-side">
          <div className="section-header">
            <h3>Audit Activity Stream</h3>
            <span className="badge-live">LIVE</span>
          </div>

          {activity.length === 0 ? (
            <div className="empty-state">No recent activity logged.</div>
          ) : (
            <ul className="activity-feed">
              {activity.slice(0, 10).map((a) => (
                <li key={a.id} className="activity-item">
                  <span className="activity-time">
                    {new Date(a.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <span className="activity-action">{a.action}</span>
                  <span className="activity-detail">{a.detail}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Quick Task Modal */}
      {quickTaskModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Quick Add Task</h3>
            <form onSubmit={handleCreateQuickTask}>
              <input
                type="text"
                autoFocus
                placeholder="Task description..."
                value={quickTaskTitle}
                onChange={(e) => setQuickTaskTitle(e.target.value)}
              />
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setQuickTaskModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Quick Project Modal */}
      {quickProjectModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Create Sovereign Project</h3>
            <form onSubmit={handleCreateQuickProject}>
              <label>Project Title</label>
              <input
                type="text"
                autoFocus
                placeholder="e.g. Distributed Core Architecture"
                value={quickProjectTitle}
                onChange={(e) => setQuickProjectTitle(e.target.value)}
                required
              />
              <label>Description</label>
              <textarea
                placeholder="High-level project scope and milestones..."
                value={quickProjectDesc}
                onChange={(e) => setQuickProjectDesc(e.target.value)}
                rows={3}
              />
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setQuickProjectModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
