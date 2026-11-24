import React, { useEffect, useState } from "react";
import { api, Note, Project } from "../api";

export function NotesView() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [projectFilter, setProjectFilter] = useState<string>("all");

  // Create / Edit modal
  const [showModal, setShowModal] = useState(false);
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [noteProjectId, setNoteProjectId] = useState<number | "">("");
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [modalError, setModalError] = useState<string | null>(null);

  async function loadData() {
    setError(null);
    try {
      const [nList, pList] = await Promise.all([api.listNotes(), api.listProjects()]);
      setNotes(nList);
      setProjects(pList);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function openCreate() {
    setEditingNote(null);
    setNoteTitle("");
    setNoteContent("");
    setNoteProjectId("");
    setSaveStatus("idle");
    setModalError(null);
    setShowModal(true);
  }

  function openEdit(n: Note) {
    setEditingNote(n);
    setNoteTitle(n.title);
    setNoteContent(n.content);
    setNoteProjectId(n.project_id ?? "");
    setSaveStatus("idle");
    setModalError(null);
    setShowModal(true);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!noteTitle.trim()) return;
    setSaveStatus("saving");
    setModalError(null);
    try {
      const pid = noteProjectId === "" ? undefined : Number(noteProjectId);
      if (editingNote) {
        await api.updateNote(editingNote.id, {
          title: noteTitle.trim(),
          content: noteContent.trim() || "No content",
          project_id: pid ?? null,
        });
      } else {
        await api.createNote(noteTitle.trim(), noteContent.trim() || "No content", pid);
      }
      setSaveStatus("saved");
      setShowModal(false);
      await loadData();
    } catch (err) {
      setSaveStatus("failed");
      setModalError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleDelete(n: Note) {
    if (!confirm(`Delete note "${n.title}"?`)) return;
    try {
      await api.deleteNote(n.id);
      loadData();
    } catch (err) {
      setError(`Error deleting note: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  const filtered = notes.filter((n) => {
    const matchesProj = projectFilter === "all" || String(n.project_id) === projectFilter;
    const matchesSearch =
      n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.content.toLowerCase().includes(search.toLowerCase());
    return matchesProj && matchesSearch;
  });

  return (
    <div className="notes-view">
      <div className="view-toolbar">
        <div className="toolbar-left">
          <h2>Notes Wall</h2>
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
          <input
            type="text"
            className="search-input"
            placeholder="Search notes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button className="btn-primary" onClick={openCreate}>
            + Write Note
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="loading-state">Loading notes...</div>
      ) : filtered.length === 0 ? (
        <div className="empty-state card">No notes found. Create your first sovereign note!</div>
      ) : (
        <div className="notes-grid">
          {filtered.map((n) => {
            const project = projects.find((p) => p.id === n.project_id);
            return (
              <div key={n.id} className="note-card card">
                <div className="note-card-head">
                  <h3 className="note-title">{n.title}</h3>
                  <div className="note-card-actions">
                    <button className="btn-icon" onClick={() => openEdit(n)} title="Edit Note">
                      ✏️
                    </button>
                    <button className="btn-icon-danger" onClick={() => handleDelete(n)} title="Delete Note">
                      ✕
                    </button>
                  </div>
                </div>

                {project && <span className="project-tag">{project.title}</span>}

                <div className="note-card-body">
                  <pre className="note-text">{n.content}</pre>
                </div>

                <div className="note-card-foot">
                  <span className="dim text-xs">Rev: {n.revision}</span>
                  <span className="dim text-xs">{new Date(n.updated_at).toLocaleDateString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Note Modal */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-card modal-large">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3>{editingNote ? "Edit Note" : "Write Sovereign Note"}</h3>
              <span className="text-xs dim">
                {saveStatus === "saving"
                  ? "Saving..."
                  : saveStatus === "saved"
                  ? "✓ Saved"
                  : saveStatus === "failed"
                  ? "✕ Save Failed"
                  : ""}
              </span>
            </div>
            <form onSubmit={handleSave}>
              <label>Title</label>
              <input
                type="text"
                autoFocus
                placeholder="Note title..."
                value={noteTitle}
                onChange={(e) => setNoteTitle(e.target.value)}
                required
              />

              <label>Project Association (Optional)</label>
              <select
                value={noteProjectId}
                onChange={(e) => setNoteProjectId(e.target.value === "" ? "" : Number(e.target.value))}
              >
                <option value="">None (Independent Note)</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>

              <label>Content (Markdown / Plain Text)</label>
              <textarea
                placeholder="Write your note contents here..."
                rows={10}
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
              />

              {modalError && <div className="error-banner">{modalError}</div>}

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={saveStatus === "saving"}>
                  {saveStatus === "saving" ? "Saving..." : editingNote ? "Save Changes" : "Create Note"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
