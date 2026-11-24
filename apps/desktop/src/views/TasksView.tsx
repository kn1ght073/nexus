import React, { useEffect, useState } from "react";
import { api, Task, Project } from "../api";

export function TasksView() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [projectFilter, setProjectFilter] = useState<string>("all");
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<number | "">("");

  async function loadData() {
    setError(null);
    try {
      const [tList, pList] = await Promise.all([api.listTasks(), api.listProjects()]);
      setTasks(tList);
      setProjects(pList);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleAddTask(e: React.FormEvent) {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    setError(null);
    try {
      const pid = selectedProjectId === "" ? undefined : Number(selectedProjectId);
      await api.createTask(newTaskTitle.trim(), pid);
      setNewTaskTitle("");
      loadData();
    } catch (err) {
      setError(`Error adding task: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  async function handleStatusChange(task: Task, newStatus: "pending" | "in_progress" | "completed") {
    setError(null);
    try {
      await api.updateTaskStatus(task.id, newStatus);
      loadData();
    } catch (err) {
      setError(`Error updating task status: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  async function handleDelete(task: Task) {
    if (!confirm(`Delete task "${task.title}"?`)) return;
    setError(null);
    try {
      await api.deleteTask(task.id);
      loadData();
    } catch (err) {
      setError(`Error deleting task: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  const filtered = tasks.filter((t) => {
    const matchStatus = statusFilter === "all" || t.status === statusFilter;
    const matchProject = projectFilter === "all" || String(t.project_id) === projectFilter;
    return matchStatus && matchProject;
  });

  return (
    <div className="tasks-view">
      <div className="view-toolbar">
        <div className="toolbar-left">
          <h2>Execution Tasks</h2>
          <div className="filter-group">
            {["all", "pending", "in_progress", "completed"].map((st) => (
              <button
                key={st}
                className={`filter-btn ${statusFilter === st ? "active" : ""}`}
                onClick={() => setStatusFilter(st)}
              >
                {st.replace("_", " ").toUpperCase()}
              </button>
            ))}
          </div>

          <select
            className="select-filter"
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
          >
            <option value="all">All Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.title}
              </option>
            ))}
          </select>
        </div>

        <div className="toolbar-right">
          <form onSubmit={handleAddTask} className="inline-add-form">
            <input
              type="text"
              placeholder="New task title..."
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
              style={{ width: "240px" }}
            />
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value === "" ? "" : Number(e.target.value))}
            >
              <option value="">No Project</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
            <button type="submit" className="btn-primary">
              + Add Task
            </button>
          </form>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        {loading ? (
          <div className="loading-state">Loading tasks...</div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">No matching tasks found.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: "60px" }}>ID</th>
                <th>Title</th>
                <th style={{ width: "160px" }}>Project</th>
                <th style={{ width: "140px" }}>Status</th>
                <th style={{ width: "60px" }}>Rev</th>
                <th style={{ width: "180px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => {
                const project = projects.find((p) => p.id === t.project_id);
                return (
                  <tr key={t.id}>
                    <td className="mono dim">#{t.id}</td>
                    <td className={t.status === "completed" ? "line-through dim" : ""}>
                      {t.title}
                    </td>
                    <td>
                      {project ? (
                        <span className="project-tag">{project.title}</span>
                      ) : (
                        <span className="dim">—</span>
                      )}
                    </td>
                    <td>
                      <select
                        className="select-status"
                        value={t.status}
                        onChange={(e) => handleStatusChange(t, e.target.value as any)}
                      >
                        <option value="pending">Pending</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                      </select>
                    </td>
                    <td className="mono">{t.revision}</td>
                    <td style={{ textAlign: "right" }}>
                      {t.status !== "completed" && (
                        <button
                          className="btn-action"
                          onClick={() => handleStatusChange(t, "completed")}
                        >
                          ✓ Done
                        </button>
                      )}
                      <button className="btn-delete" onClick={() => handleDelete(t)}>
                        ✕
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
