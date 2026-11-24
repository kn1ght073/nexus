import React, { useEffect, useState } from "react";
import { api, Project, Task, Note } from "../api";

export function ProjectsView() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  // Modal create
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  // Drilldown project drawer
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [projectTasks, setProjectTasks] = useState<Task[]>([]);
  const [projectNotes, setProjectNotes] = useState<Note[]>([]);
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newNoteTitle, setNewNoteTitle] = useState("");
  const [newNoteContent, setNewNoteContent] = useState("");

  async function loadProjects() {
    setError(null);
    try {
      const data = await api.listProjects();
      setProjects(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function loadProjectDetails(proj: Project) {
    setSelectedProject(proj);
    try {
      const [tList, nList] = await Promise.all([
        api.listTasks(proj.id),
        api.listNotes(proj.id),
      ]);
      setProjectTasks(tList);
      setProjectNotes(nList);
    } catch (err) {
      console.error(err);
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      await api.createProject(title.trim(), description.trim());
      setTitle("");
      setDescription("");
      setShowCreate(false);
      loadProjects();
    } catch (err) {
      alert(`Error creating project: ${err}`);
    }
  }

  async function handleStatusChange(proj: Project, nextStatus: string) {
    try {
      const updated = await api.updateProjectStatus(proj.id, nextStatus);
      if (selectedProject?.id === proj.id) {
        setSelectedProject(updated);
      }
      loadProjects();
    } catch (err) {
      alert(`Error updating project status: ${err}`);
    }
  }

  async function handleDelete(proj: Project) {
    if (!confirm(`Are you sure you want to delete project "${proj.title}"?`)) return;
    try {
      await api.deleteProject(proj.id);
      if (selectedProject?.id === proj.id) {
        setSelectedProject(null);
      }
      loadProjects();
    } catch (err) {
      alert(`Error deleting project: ${err}`);
    }
  }

  async function handleAddTaskToProject(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProject || !newTaskTitle.trim()) return;
    try {
      await api.createTask(newTaskTitle.trim(), selectedProject.id);
      setNewTaskTitle("");
      const tList = await api.listTasks(selectedProject.id);
      setProjectTasks(tList);
    } catch (err) {
      alert(`Error adding task: ${err}`);
    }
  }

  async function handleAddNoteToProject(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProject || !newNoteTitle.trim()) return;
    try {
      await api.createNote(newNoteTitle.trim(), newNoteContent.trim() || "No content", selectedProject.id);
      setNewNoteTitle("");
      setNewNoteContent("");
      const nList = await api.listNotes(selectedProject.id);
      setProjectNotes(nList);
    } catch (err) {
      alert(`Error adding note: ${err}`);
    }
  }

  const filtered = projects.filter((p) => {
    const matchesFilter = filter === "all" || p.status.toLowerCase() === filter.toLowerCase();
    const matchesSearch = p.title.toLowerCase().includes(search.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(search.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="projects-view">
      <div className="view-toolbar">
        <div className="toolbar-left">
          <h2>Projects</h2>
          <div className="filter-group">
            {["all", "active", "completed", "archived"].map((f) => (
              <button
                key={f}
                className={`filter-btn ${filter === f ? "active" : ""}`}
                onClick={() => setFilter(f)}
              >
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="toolbar-right">
          <input
            type="text"
            className="search-input"
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button className="btn-primary" onClick={() => setShowCreate(true)}>
            + New Project
          </button>
        </div>
      </div>

      {error && <div className="error-banner">Error: {error}</div>}

      <div className="projects-table-container card">
        {loading ? (
          <div className="loading-state">Loading projects...</div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">No matching projects found.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: "60px" }}>ID</th>
                <th>Title & Description</th>
                <th style={{ width: "120px" }}>Status</th>
                <th style={{ width: "80px" }}>Rev</th>
                <th style={{ width: "140px" }}>Updated</th>
                <th style={{ width: "220px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id} className={selectedProject?.id === p.id ? "row-selected" : ""}>
                  <td className="mono dim">#{p.id}</td>
                  <td>
                    <div className="table-item-title" onClick={() => loadProjectDetails(p)}>
                      {p.title}
                    </div>
                    {p.description && <div className="table-item-sub">{p.description}</div>}
                  </td>
                  <td>
                    <span className={`badge badge-${p.status.toLowerCase()}`}>{p.status}</span>
                  </td>
                  <td className="mono">{p.revision}</td>
                  <td className="dim text-sm">{new Date(p.updated_at).toLocaleDateString()}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn-action" onClick={() => loadProjectDetails(p)}>
                      Inspect
                    </button>
                    <select
                      className="select-status"
                      value={p.status}
                      onChange={(e) => handleStatusChange(p, e.target.value)}
                    >
                      <option value="active">Active</option>
                      <option value="completed">Completed</option>
                      <option value="archived">Archived</option>
                    </select>
                    <button className="btn-delete" onClick={() => handleDelete(p)}>
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Project Drilldown Drawer */}
      {selectedProject && (
        <div className="drilldown-drawer card">
          <div className="drawer-header">
            <div>
              <h3>{selectedProject.title}</h3>
              <div className="dim text-sm">
                Project #{selectedProject.id} · Rev: {selectedProject.revision} · Created:{" "}
                {new Date(selectedProject.created_at).toLocaleDateString()}
              </div>
            </div>
            <button className="btn-close" onClick={() => setSelectedProject(null)}>
              ✕ Close
            </button>
          </div>

          {selectedProject.description && (
            <p className="project-desc">{selectedProject.description}</p>
          )}

          <div className="drawer-grid">
            {/* Project Tasks */}
            <div className="drawer-subcard">
              <h4>Tasks ({projectTasks.length})</h4>
              <form onSubmit={handleAddTaskToProject} className="inline-add-form">
                <input
                  type="text"
                  placeholder="Add task to this project..."
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                />
                <button type="submit" className="btn-primary">
                  Add
                </button>
              </form>

              <div className="drawer-items-list">
                {projectTasks.length === 0 ? (
                  <div className="dim text-sm">No tasks assigned to this project.</div>
                ) : (
                  projectTasks.map((t) => (
                    <div key={t.id} className="drawer-item-row">
                      <span className={t.status === "completed" ? "line-through dim" : ""}>
                        #{t.id} {t.title}
                      </span>
                      {t.status !== "completed" ? (
                        <button
                          className="btn-done-sm"
                          onClick={async () => {
                            await api.completeTask(t.id);
                            const tList = await api.listTasks(selectedProject.id);
                            setProjectTasks(tList);
                          }}
                        >
                          Done
                        </button>
                      ) : (
                        <span className="badge badge-completed">Done</span>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Project Notes */}
            <div className="drawer-subcard">
              <h4>Notes ({projectNotes.length})</h4>
              <form onSubmit={handleAddNoteToProject} className="inline-add-form" style={{ flexDirection: "column" }}>
                <input
                  type="text"
                  placeholder="Note title..."
                  value={newNoteTitle}
                  onChange={(e) => setNewNoteTitle(e.target.value)}
                />
                <textarea
                  placeholder="Content..."
                  rows={2}
                  value={newNoteContent}
                  onChange={(e) => setNewNoteContent(e.target.value)}
                />
                <button type="submit" className="btn-primary" style={{ alignSelf: "flex-end" }}>
                  Attach Note
                </button>
              </form>

              <div className="drawer-items-list">
                {projectNotes.length === 0 ? (
                  <div className="dim text-sm">No notes attached.</div>
                ) : (
                  projectNotes.map((n) => (
                    <div key={n.id} className="note-mini-card">
                      <div className="note-mini-title">{n.title}</div>
                      <div className="note-mini-content">{n.content}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>New Sovereign Project</h3>
            <form onSubmit={handleCreate}>
              <label>Title</label>
              <input
                type="text"
                autoFocus
                placeholder="e.g. Distributed Core Service"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
              <label>Description</label>
              <textarea
                placeholder="Objectives, deliverables, notes..."
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>
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
