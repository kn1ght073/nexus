import React, { useEffect, useRef, useState } from "react";
import { api, FileItem } from "../api";

export function FilesView() {
  const [roots, setRoots] = useState<string[]>([]);
  const [currentPath, setCurrentPath] = useState<string>("");
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Array<{ path: string; match_context: string }> | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadRootsAndFiles() {
    setError(null);
    try {
      const r = await api.listRoots();
      setRoots(r);
      const initialPath = currentPath || (r.length > 0 ? r[0] : "");
      setCurrentPath(initialPath);
      if (initialPath) {
        const list = await api.browseFiles(initialPath);
        setFiles(list);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function navigateTo(path: string) {
    setError(null);
    setLoading(true);
    setSearchResults(null);
    try {
      const list = await api.browseFiles(path);
      setCurrentPath(path);
      setFiles(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  function navigateUp() {
    if (!currentPath) return;
    const parts = currentPath.split("/").filter(Boolean);
    if (parts.length <= 1) return;
    parts.pop();
    const parent = "/" + parts.join("/");
    navigateTo(parent);
  }

  useEffect(() => {
    loadRootsAndFiles();
  }, []);

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const selectedFiles = e.target.files;
    if (!selectedFiles || selectedFiles.length === 0) return;
    const file = selectedFiles[0];
    setUploading(true);
    setError(null);
    try {
      await api.uploadFile(file, currentPath);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await navigateTo(currentPath);
    } catch (err) {
      setError(`Upload failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setUploading(false);
    }
  }

  async function handleDownloadFile(file: FileItem) {
    setError(null);
    try {
      await api.downloadFile(file.path, file.name);
    } catch (err) {
      setError(`Download failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  async function handleDeleteFile(file: FileItem) {
    if (!confirm(`Delete "${file.name}"? This action is permanent.`)) return;
    try {
      await api.deleteFile(file.path);
      navigateTo(currentPath);
    } catch (err) {
      setError(`Delete failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.searchFiles(searchQuery.trim(), currentPath);
      setSearchResults(res);
    } catch (err) {
      setError(`Search failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  return (
    <div className="files-view">
      <div className="view-toolbar">
        <div className="toolbar-left">
          <h2>Shared Files</h2>
          {roots.length > 0 && (
            <select
              className="select-filter"
              value={roots.find((r) => currentPath.startsWith(r)) ?? roots[0]}
              onChange={(e) => navigateTo(e.target.value)}
            >
              {roots.map((r) => (
                <option key={r} value={r}>
                  Root: {r}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="toolbar-right">
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              className="search-input"
              placeholder="Search file contents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button type="submit" className="btn-secondary">
              Search
            </button>
            {searchResults !== null && (
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  setSearchResults(null);
                  setSearchQuery("");
                }}
              >
                Clear
              </button>
            )}
          </form>

          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            onChange={handleFileUpload}
          />
          <button
            className="btn-primary"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? "Uploading..." : "↑ Upload File"}
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* Path Breadcrumbs */}
      <div className="breadcrumb-bar card">
        <button className="btn-action" onClick={navigateUp} title="Go Up Directory">
          ⬆ Up
        </button>
        <span className="current-path mono">{currentPath || "/"}</span>
        <button className="btn-action" onClick={() => navigateTo(currentPath)}>
          🔄 Refresh
        </button>
      </div>

      {/* Search results view */}
      {searchResults !== null ? (
        <div className="card">
          <h3>Search Results for "{searchQuery}" ({searchResults.length})</h3>
          {searchResults.length === 0 ? (
            <div className="empty-state">No matching content found in this storage root.</div>
          ) : (
            <ul className="search-results-list">
              {searchResults.map((sr, idx) => (
                <li key={idx} className="search-result-item">
                  <div className="mono text-sm search-result-path">{sr.path}</div>
                  <div className="search-result-snippet">{sr.match_context}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        /* File Table */
        <div className="card">
          {loading ? (
            <div className="loading-state">Loading directory contents...</div>
          ) : files.length === 0 ? (
            <div className="empty-state">Directory is empty. Upload files to get started.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: "40px" }}></th>
                  <th>Name</th>
                  <th style={{ width: "110px" }}>Size</th>
                  <th style={{ width: "160px" }}>Modified</th>
                  <th style={{ width: "200px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr key={f.path}>
                    <td style={{ fontSize: "18px" }}>{f.is_dir ? "📁" : "📄"}</td>
                    <td>
                      {f.is_dir ? (
                        <span
                          className="file-link folder-link"
                          onClick={() => navigateTo(f.path)}
                        >
                          {f.name}
                        </span>
                      ) : (
                        <span className="file-name">{f.name}</span>
                      )}
                    </td>
                    <td className="mono dim">{f.is_dir ? "—" : formatBytes(f.size)}</td>
                    <td className="dim text-sm">
                      {f.modified_at ? new Date(f.modified_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {!f.is_dir && (
                        <button
                          className="btn-action"
                          onClick={() => handleDownloadFile(f)}
                        >
                          ↓ Download
                        </button>
                      )}
                      {!f.is_dir && (
                        <button className="btn-delete" onClick={() => handleDeleteFile(f)}>
                          ✕
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
