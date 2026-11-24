/**
 * NEXUS Desktop API client.
 *
 * Interfaces with NEXUS Core API on the primary host (Mac loopback http://127.0.0.1:8000
 * or cloud relay proxy). Authoritative state lives in the local SQLite database.
 */

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  status: "pending" | "in_progress" | "completed";
  project_id: number | null;
  revision: number;
  updated_at: string;
}

export interface Project {
  id: number;
  title: string;
  description: string | null;
  status: string;
  revision: number;
  created_at: string;
  updated_at: string;
}

export interface Note {
  id: number;
  title: string;
  content: string;
  project_id: number | null;
  revision: number;
  created_at: string;
  updated_at: string;
}

export interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
}

export interface Device {
  id: number;
  name: string;
  platform: string;
  capabilities: string[];
  is_online: boolean;
  last_seen?: string;
}

export interface ActiveNode {
  node_id: string;
  name: string;
  is_active: boolean;
  lan_url?: string | null;
  relay_proxy_url?: string | null;
  claimed_at?: string;
  last_seen_at?: string;
}

export interface ActivityItem {
  id: number;
  action: string;
  detail: string;
  created_at: string;
}

const DEFAULT_LOCAL_BASE = "http://127.0.0.1:8000";
const CLOUD_BASE = "https://nexus-control-plane-uvi8.onrender.com";

function headers(): Record<string, string> {
  const token = localStorage.getItem("nexus.token");
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function request<T>(path: string, init?: RequestInit, baseOverride?: string): Promise<T> {
  const base = baseOverride ?? api.getBaseUrl();
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: { ...headers(), ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  getBaseUrl(): string {
    return localStorage.getItem("nexus.core") ?? DEFAULT_LOCAL_BASE;
  },

  setBaseUrl(url: string) {
    localStorage.setItem("nexus.core", url.trim());
  },

  getCloudBaseUrl(): string {
    return CLOUD_BASE;
  },

  getLocalBaseUrl(): string {
    return DEFAULT_LOCAL_BASE;
  },

  setToken(token: string) {
    localStorage.setItem("nexus.token", token.trim());
  },

  clearToken() {
    localStorage.removeItem("nexus.token");
  },

  hasToken(): boolean {
    return localStorage.getItem("nexus.token") !== null;
  },

  getToken(): string | null {
    return localStorage.getItem("nexus.token");
  },

  async health(targetUrl?: string): Promise<{ status: string; service: string; version?: string }> {
    return request("/health", undefined, targetUrl);
  },

  async me(): Promise<User> {
    return request("/api/auth/me");
  },

  async loginWithToken(token: string): Promise<User> {
    this.setToken(token);
    try {
      return await this.me();
    } catch (e) {
      this.clearToken();
      throw e;
    }
  },

  // --- Projects ---
  async listProjects(statusFilter?: string): Promise<Project[]> {
    const q = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
    return request(`/api/projects${q}`);
  },

  async getProject(id: number): Promise<Project> {
    return request(`/api/projects/${id}`);
  },

  async createProject(title: string, description?: string): Promise<Project> {
    return request("/api/projects", {
      method: "POST",
      body: JSON.stringify({ title, description: description || null }),
    });
  },

  async updateProjectStatus(id: number, status: string): Promise<Project> {
    return request(`/api/projects/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  },

  async deleteProject(id: number): Promise<void> {
    return request(`/api/projects/${id}`, { method: "DELETE" });
  },

  // --- Tasks ---
  async listTasks(projectId?: number, statusFilter?: string): Promise<Task[]> {
    const params = new URLSearchParams();
    if (projectId !== undefined) params.set("project_id", String(projectId));
    if (statusFilter) params.set("status_filter", statusFilter);
    const qs = params.toString();
    return request(`/api/tasks${qs ? `?${qs}` : ""}`);
  },

  async createTask(title: string, projectId?: number): Promise<Task> {
    return request("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ title, project_id: projectId ?? null }),
    });
  },

  async updateTaskStatus(id: number, status: "pending" | "in_progress" | "completed"): Promise<Task> {
    return request(`/api/tasks/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  },

  async completeTask(taskId: number): Promise<Task> {
    return request(`/api/tasks/${taskId}/done`, { method: "POST" });
  },

  async deleteTask(taskId: number): Promise<void> {
    return request(`/api/tasks/${taskId}`, { method: "DELETE" });
  },

  // --- Notes ---
  async listNotes(projectId?: number): Promise<Note[]> {
    const q = projectId !== undefined ? `?project_id=${projectId}` : "";
    return request(`/api/notes${q}`);
  },

  async getNote(id: number): Promise<Note> {
    return request(`/api/notes/${id}`);
  },

  async createNote(title: string, content: string, projectId?: number): Promise<Note> {
    return request("/api/notes", {
      method: "POST",
      body: JSON.stringify({ title, content, project_id: projectId ?? null }),
    });
  },

  async updateNote(id: number, data: { title?: string; content?: string; project_id?: number | null }): Promise<Note> {
    return request(`/api/notes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteNote(noteId: number): Promise<void> {
    return request(`/api/notes/${noteId}`, { method: "DELETE" });
  },

  // --- Files & Storage ---
  async listRoots(): Promise<string[]> {
    return request("/api/files/roots");
  },

  async browseFiles(path?: string): Promise<FileItem[]> {
    const q = path ? `?path=${encodeURIComponent(path)}` : "";
    return request(`/api/files/browse${q}`);
  },

  async searchFiles(query: string, path?: string): Promise<Array<{ path: string; match_context: string }>> {
    const params = new URLSearchParams({ query });
    if (path) params.set("path", path);
    return request(`/api/files/search?${params.toString()}`);
  },

  async uploadFile(file: File, directory?: string): Promise<FileItem> {
    const base = api.getBaseUrl();
    const token = localStorage.getItem("nexus.token");
    const formData = new FormData();
    formData.append("file", file);

    const q = directory ? `?directory=${encodeURIComponent(directory)}` : "";
    const res = await fetch(`${base}/api/files/upload${q}`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`${res.status}: ${err}`);
    }
    return (await res.json()) as FileItem;
  },

  getDownloadUrl(path: string): string {
    const base = api.getBaseUrl();
    const token = localStorage.getItem("nexus.token");
    return `${base}/api/files/download?path=${encodeURIComponent(path)}${token ? `&token=${encodeURIComponent(token)}` : ""}`;
  },

  async deleteFile(path: string): Promise<void> {
    const q = `?path=${encodeURIComponent(path)}`;
    return request(`/api/files/delete${q}`, { method: "DELETE" });
  },

  // --- Devices & Nodes ---
  async listDevices(): Promise<Device[]> {
    return request("/api/devices");
  },

  async getActiveNode(): Promise<ActiveNode | null> {
    try {
      return await request<ActiveNode>("/api/nodes/active");
    } catch {
      return null;
    }
  },

  async activity(limit = 30): Promise<ActivityItem[]> {
    return request(`/api/activity?limit=${limit}`);
  },
};
