import React, { useEffect, useState } from "react";
import { api, Project, Task, Note } from "../api";

export function ProjectsView() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  // Modal create / edit
  const [showCreate, setShowCreate] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

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
      setError(e instanceof Error ? e.message : String(e));
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
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  function openCreateModal() {
    setEditingProject(null);
    setTitle("");
    setDescription("");
    setModalError(null);
    setShowCreate(true);
  }

  function openEditModal(proj: Project) {
    setEditingProject(proj);
    setTitle(proj.title);
    setDescription(proj.description ?? "");
    setModalError(null);
    setShowCreate(true);
  }

  async function handleSaveProject(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setModalError(null);
    try {
      if (editingProject) {
        const updated = await api.updateProject(editingProject.id, {
          title: title.trim(),
          description: description.trim() || null,
        });
        if (selectedProject?.id === updated.id) {
          setSelectedProject(updated);
        }
      } else {
        await api.createProject(title.trim(), description.trim());
      }
      setTitle("");
      setDescription("");
      setShowCreate(false);
      setEditingProject(null);
      await loadProjects();
    } catch (err) {
      setModalError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(proj: Project, nextStatus: "pending" | "in_progress" | "completed") {
    try {
      const updated = await api.updateProjectStatus(proj.id, nextStatus);
      if (selectedProject?.id === proj.id) {
        setSelectedProject(updated);
      }
      loadProjects();
    } catch (err) {
      setError(`Error updating project status: ${err}`);
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
      setError(`Error deleting project: ${err}`);
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
      setError(`Error adding task: ${err}`);
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
      setError(`Error adding note: ${err}`);
    }
  }

  const filtered = projects.filter((p) => {
    const matchesFilter = filter === "all" || p.status.toLowerCase() === filter.toLowerCase();
    const matchesSearch =
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(search.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="projects-view">
      <div className="view-toolbar">
        <div className="toolbar-left">
          <h2>Projects</h2>
          <div className="filter-group">
            {[
              { id: "all", label: "ALL" },
              { id: "pending", label: "PENDING" },
              { id: "in_progress", label: "IN PROGRESS" },
              { id: "completed", label: "COMPLETED" },
            ].map((f) => (
              <button
                key={f.id}
                className={`filter-btn ${filter === f.id ? "active" : ""}`}
                onClick={() => setFilter(f.id)}
              >
                {f.label}
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
          <button className="btn-primary" onClick={openCreateModal}>
            + New Project
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

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
                <th style={{ width: "130px" }}>Status</th>
                <th style={{ width: "70px" }}>Rev</th>
                <th style={{ width: "130px" }}>Updated</th>
                <th style={{ width: "260px", textAlign: "right" }}>Actions</th>
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
                    <span className={`badge badge-${p.status.toLowerCase()}`}>
                      {p.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="mono">{p.revision}</td>
                  <td className="dim text-sm">{new Date(p.updated_at).toLocaleDateString()}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn-action" onClick={() => loadProjectDetails(p)}>
                      Inspect
                    </button>
                    <button className="btn-action" style={{ marginLeft: "6px" }} onClick={() => openEditModal(p)}>
                      Edit
                    </button>
                    <select
                      className="select-status"
                      style={{ marginLeft: "6px" }}
                      value={p.status}
                      onChange={(e) => handleStatusChange(p, e.target.value as any)}
                    >
                      <option value="pending">Pending</option>
                      <option value="in_progress">In Progress</option>
                      <option value="completed">Completed</option>
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
        <div className="drilldown-drawer card" style={{ marginTop: "20px" }}>
          <div className="drawer-header">
            <div>
              <h3>{selectedProject.title}</h3>
              <div className="dim text-sm">
                Project #{selectedProject.id} · Rev: {selectedProject.revision} · Created:{" "}
                {new Date(selectedProject.created_at).toLocaleDateString()} · Updated:{" "}
                {new Date(selectedProject.updated_at).toLocaleString()}
              </div>
            </div>
            <button className="btn-secondary" onClick={() => setSelectedProject(null)}>
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
                          className="btn-done"
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

      {/* Create / Edit Modal */}
      {showCreate && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>{editingProject ? "Edit Sovereign Project" : "New Sovereign Project"}</h3>
            <form onSubmit={handleSaveProject}>
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
              {modalError && <div className="error-banner">{modalError}</div>}
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? "Saving..." : editingProject ? "Save Project" : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
