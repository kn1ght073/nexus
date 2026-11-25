/**
 * NEXUS Desktop API client.
 *
 * Separates Control Plane authentication/discovery (Render) from Authoritative
 * Host Node storage/data APIs (Mac loopback http://127.0.0.1:8000, LAN, or
 * encrypted Control Plane relay proxy). Personal records always live on the Mac Host.
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
  status: "pending" | "in_progress" | "completed";
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
  modified_at?: string | null;
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
  id?: number;
  node_id?: string;
  name: string;
  is_active: boolean;
  lan_url?: string | null;
  relay_proxy_url?: string | null;
  claimed_at?: string;
  last_seen?: string;
  last_seen_at?: string;
}

export interface ActivityItem {
  id: number;
  action: string;
  detail: string;
  created_at: string;
}

export type HostMode = "local" | "lan" | "relay" | "none";

const DEFAULT_LOCAL_BASE = "http://127.0.0.1:8000";
const CLOUD_BASE = "https://nexus-control-plane-uvi8.onrender.com";

export function normalizeBaseUrl(url: string): string {
  if (!url) return "";
  return url.trim().replace(/\/+$/, "");
}

export function cleanToken(raw: string): string {
  if (!raw) return "";
  let t = raw.trim();
  if (t.toLowerCase().startsWith("bearer ")) {
    t = t.substring(7).trim();
  }
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    t = t.slice(1, -1).trim();
  }
  return t;
}

function authHeaders(forHost = false): Record<string, string> {
  const cpToken = localStorage.getItem("nexus.token");
  const hostToken = localStorage.getItem("nexus.host_token");
  const mode = (localStorage.getItem("nexus.host_mode") as HostMode | null) ?? "none";
  const h: Record<string, string> = { "Content-Type": "application/json" };

  if (forHost && mode === "relay") {
    if (cpToken) h["Authorization"] = `Bearer ${cpToken}`;
    if (hostToken) h["X-Nexus-Node-Authorization"] = `Bearer ${hostToken}`;
  } else if (forHost) {
    const tok = hostToken || cpToken;
    if (tok) h["Authorization"] = `Bearer ${tok}`;
  } else {
    const tok = cpToken || hostToken;
    if (tok) h["Authorization"] = `Bearer ${tok}`;
  }
  return h;
}

async function rawRequest<T>(
  path: string,
  init?: RequestInit,
  baseOverride?: string,
  forHost = false
): Promise<T> {
  const base = normalizeBaseUrl(baseOverride ?? (forHost ? api.getHostUrl() : api.getBaseUrl()));
  if (forHost && base === CLOUD_BASE) {
    throw new Error("Mac Host Node is offline. Start your local Mac host (port 8000) or bring an active node online.");
  }
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(`${base}${cleanPath}`, {
    ...init,
    headers: { ...authHeaders(forHost), ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function exchangeCpTokenOnHost(hostUrl: string, cpToken: string, relayMode = false): Promise<string | null> {
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (relayMode) {
      headers["Authorization"] = `Bearer ${cpToken}`;
    }
    const res = await fetch(`${normalizeBaseUrl(hostUrl)}/api/auth/cp-exchange`, {
      method: "POST",
      headers,
      body: JSON.stringify({ token: cpToken }),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { access_token?: string };
    return data.access_token ? cleanToken(data.access_token) : null;
  } catch {
    return null;
  }
}

async function hostRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let hostUrl = api.getHostUrl();
  let mode = api.getHostMode();

  if (!hostUrl || mode === "none") {
    await api.resolveHost();
    hostUrl = api.getHostUrl();
    mode = api.getHostMode();
  }

  if (!hostUrl || mode === "none") {
    throw new Error("Mac Host Node is offline. Start your local Mac host (port 8000) or bring an active node online.");
  }

  try {
    return await rawRequest<T>(path, init, hostUrl, true);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const cpToken = api.getToken();
    if (msg.startsWith("401:") && cpToken && (mode === "local" || mode === "lan")) {
      const exchanged = await exchangeCpTokenOnHost(hostUrl, cpToken, false);
      if (exchanged) {
        api.setHostToken(exchanged);
        return await rawRequest<T>(path, init, hostUrl, true);
      }
    }
    throw err;
  }
}

export const api = {
  getBaseUrl(): string {
    const stored = localStorage.getItem("nexus.core");
    return stored ? normalizeBaseUrl(stored) : DEFAULT_LOCAL_BASE;
  },

  setBaseUrl(url: string) {
    localStorage.setItem("nexus.core", normalizeBaseUrl(url));
  },

  getHostUrl(): string {
    const raw = normalizeBaseUrl(localStorage.getItem("nexus.host") ?? "");
    if (raw === CLOUD_BASE) return "";
    return raw;
  },

  getHostMode(): HostMode {
    return (localStorage.getItem("nexus.host_mode") as HostMode | null) ?? "none";
  },

  setHostConnection(url: string, mode: HostMode) {
    if (url) {
      localStorage.setItem("nexus.host", normalizeBaseUrl(url));
    } else {
      localStorage.removeItem("nexus.host");
    }
    localStorage.setItem("nexus.host_mode", mode);
  },

  getCloudBaseUrl(): string {
    return CLOUD_BASE;
  },

  getLocalBaseUrl(): string {
    return DEFAULT_LOCAL_BASE;
  },

  isLocalUrl(url: string): boolean {
    const norm = normalizeBaseUrl(url);
    return norm === DEFAULT_LOCAL_BASE || norm === "http://localhost:8000";
  },

  isCloudUrl(url: string): boolean {
    const norm = normalizeBaseUrl(url);
    return norm === CLOUD_BASE;
  },

  cleanToken(raw: string): string {
    return cleanToken(raw);
  },

  setToken(token: string) {
    localStorage.setItem("nexus.token", cleanToken(token));
  },

  setHostToken(token: string) {
    localStorage.setItem("nexus.host_token", cleanToken(token));
  },

  clearToken() {
    localStorage.removeItem("nexus.token");
    localStorage.removeItem("nexus.host_token");
    localStorage.removeItem("nexus.host");
    localStorage.removeItem("nexus.host_mode");
  },

  hasToken(): boolean {
    return localStorage.getItem("nexus.token") !== null || localStorage.getItem("nexus.host_token") !== null;
  },

  getToken(): string | null {
    return localStorage.getItem("nexus.token");
  },

  getHostToken(): string | null {
    return localStorage.getItem("nexus.host_token");
  },

  async health(targetUrl?: string, timeoutMs = 4000): Promise<{ status: string; service: string; mode?: string; version?: string }> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await rawRequest("/health", { signal: controller.signal }, targetUrl);
    } finally {
      clearTimeout(id);
    }
  },

  async me(): Promise<User> {
    return rawRequest("/api/auth/me");
  },

  async resolveHost(): Promise<{ mode: HostMode; url: string }> {
    const cpToken = this.getToken();
    const currentBase = this.getBaseUrl();

    // 1. Always prefer local authoritative Mac host on 127.0.0.1:8000 if reachable
    try {
      const localHealth = await this.health(DEFAULT_LOCAL_BASE, 1500);
      if (localHealth.status === "ok" && localHealth.mode !== "control-plane") {
        let localValid = false;
        if (this.getHostToken()) {
          try {
            await rawRequest<User>("/api/auth/me", undefined, DEFAULT_LOCAL_BASE, true);
            localValid = true;
          } catch {
            localStorage.removeItem("nexus.host_token");
          }
        }
        if (!localValid && cpToken) {
          try {
            await rawRequest<User>("/api/auth/me", undefined, DEFAULT_LOCAL_BASE, false);
            this.setHostToken(cpToken);
            localValid = true;
          } catch {
            const exchanged = await exchangeCpTokenOnHost(DEFAULT_LOCAL_BASE, cpToken, false);
            if (exchanged) {
              this.setHostToken(exchanged);
              localValid = true;
            }
          }
        }
        if (localValid) {
          this.setHostConnection(DEFAULT_LOCAL_BASE, "local");
          return { mode: "local", url: DEFAULT_LOCAL_BASE };
        }
        // If local host responded healthy with mode='node', it is the authoritative host
        this.setHostConnection(DEFAULT_LOCAL_BASE, "local");
        return { mode: "local", url: DEFAULT_LOCAL_BASE };
      }
    } catch {
      // Local host unreachable; check control-plane active node
    }

    // 2. If configured explicitly to a custom non-control-plane node URL
    if (!this.isCloudUrl(currentBase) && !this.isLocalUrl(currentBase)) {
      try {
        const h = await this.health(currentBase, 2000);
        if (h.status === "ok" && h.mode !== "control-plane") {
          this.setHostConnection(currentBase, "lan");
          return { mode: "lan", url: currentBase };
        }
      } catch {
        // Unreachable
      }
    }

    // 3. Query Control Plane for active claimed node (LAN or encrypted relay proxy)
    if (cpToken) {
      try {
        const node = await rawRequest<ActiveNode | null>("/api/nodes/active", undefined, CLOUD_BASE, false);
        if (node && (node.id || node.node_id)) {
          if (node.lan_url && node.lan_url.startsWith("http")) {
            try {
              const lanHealth = await this.health(node.lan_url, 1500);
              if (lanHealth.status === "ok" && lanHealth.mode !== "control-plane") {
                const exchanged = await exchangeCpTokenOnHost(node.lan_url, cpToken, false);
                if (exchanged) this.setHostToken(exchanged);
                this.setHostConnection(node.lan_url, "lan");
                return { mode: "lan", url: node.lan_url };
              }
            } catch {
              // LAN unreachable from current network; use relay
            }
          }
          const relayUrl = node.relay_proxy_url
            ? (node.relay_proxy_url.startsWith("http") ? node.relay_proxy_url : `${CLOUD_BASE}${node.relay_proxy_url}`)
            : `${CLOUD_BASE}/api/relay/proxy`;
          const exchanged = await exchangeCpTokenOnHost(relayUrl, cpToken, true);
          if (exchanged) this.setHostToken(exchanged);
          this.setHostConnection(relayUrl, "relay");
          return { mode: "relay", url: relayUrl };
        }
      } catch {
        // No active node
      }
    }

    this.setHostConnection("", "none");
    return { mode: "none", url: "" };
  },

  async loginWithToken(token: string): Promise<User> {
    const cleaned = cleanToken(token);
    this.setToken(cleaned);
    const primaryBase = normalizeBaseUrl(this.getBaseUrl());
    const isCloudPrimary = this.isCloudUrl(primaryBase);
    const fallbackBase = isCloudPrimary ? DEFAULT_LOCAL_BASE : CLOUD_BASE;

    let user: User | null = null;
    try {
      user = await rawRequest<User>("/api/auth/me", undefined, primaryBase, false);
    } catch (primaryErr) {
      try {
        user = await rawRequest<User>("/api/auth/me", undefined, fallbackBase, false);
        this.setBaseUrl(fallbackBase);
      } catch (fallbackErr) {
        this.clearToken();
        const primMsg = primaryErr instanceof Error ? primaryErr.message : String(primaryErr);
        const fbMsg = fallbackErr instanceof Error ? fallbackErr.message : String(fallbackErr);
        throw new Error(`Auth failed on ${primaryBase} (${primMsg}) and fallback ${fallbackBase} (${fbMsg})`);
      }
    }

    await this.resolveHost();
    return user;
  },

  // --- Projects ---
  async listProjects(statusFilter?: string): Promise<Project[]> {
    const q = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
    return hostRequest(`/api/projects${q}`);
  },

  async getProject(id: number): Promise<Project> {
    return hostRequest(`/api/projects/${id}`);
  },

  async createProject(title: string, description?: string): Promise<Project> {
    return hostRequest("/api/projects", {
      method: "POST",
      body: JSON.stringify({ title, description: description || null }),
    });
  },

  async updateProject(
    id: number,
    data: { title?: string; description?: string | null; status?: "pending" | "in_progress" | "completed" }
  ): Promise<Project> {
    return hostRequest(`/api/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async updateProjectStatus(id: number, status: string): Promise<Project> {
    return hostRequest(`/api/projects/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  },

  async deleteProject(id: number): Promise<void> {
    return hostRequest(`/api/projects/${id}`, { method: "DELETE" });
  },

  // --- Tasks ---
  async listTasks(projectId?: number, statusFilter?: string): Promise<Task[]> {
    const params = new URLSearchParams();
    if (projectId !== undefined) params.set("project_id", String(projectId));
    if (statusFilter) params.set("status_filter", statusFilter);
    const qs = params.toString();
    return hostRequest(`/api/tasks${qs ? `?${qs}` : ""}`);
  },

  async createTask(title: string, projectId?: number): Promise<Task> {
    return hostRequest("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ title, project_id: projectId ?? null }),
    });
  },

  async updateTaskStatus(id: number, status: "pending" | "in_progress" | "completed"): Promise<Task> {
    return hostRequest(`/api/tasks/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  },

  async completeTask(taskId: number): Promise<Task> {
    return hostRequest(`/api/tasks/${taskId}/done`, { method: "POST" });
  },

  async deleteTask(taskId: number): Promise<void> {
    return hostRequest(`/api/tasks/${taskId}`, { method: "DELETE" });
  },

  // --- Notes ---
  async listNotes(projectId?: number): Promise<Note[]> {
    const q = projectId !== undefined ? `?project_id=${projectId}` : "";
    return hostRequest(`/api/notes${q}`);
  },

  async getNote(id: number): Promise<Note> {
    return hostRequest(`/api/notes/${id}`);
  },

  async createNote(title: string, content: string, projectId?: number): Promise<Note> {
    return hostRequest("/api/notes", {
      method: "POST",
      body: JSON.stringify({ title, content, project_id: projectId ?? null }),
    });
  },

  async updateNote(id: number, data: { title?: string; content?: string; project_id?: number | null }): Promise<Note> {
    return hostRequest(`/api/notes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteNote(noteId: number): Promise<void> {
    return hostRequest(`/api/notes/${noteId}`, { method: "DELETE" });
  },

  // --- Files & Storage ---
  async listRoots(): Promise<string[]> {
    return hostRequest("/api/files/roots");
  },

  async browseFiles(path?: string): Promise<FileItem[]> {
    const q = path ? `?path=${encodeURIComponent(path)}` : "";
    return hostRequest(`/api/files/browse${q}`);
  },

  async searchFiles(query: string, path?: string): Promise<Array<{ path: string; match_context: string }>> {
    const params = new URLSearchParams({ query });
    if (path) params.set("path", path);
    return hostRequest(`/api/files/search?${params.toString()}`);
  },

  async uploadFile(file: File, directory?: string): Promise<FileItem> {
    let hostUrl = api.getHostUrl();
    let mode = api.getHostMode();
    if (!hostUrl || mode === "none") {
      await api.resolveHost();
      hostUrl = api.getHostUrl();
      mode = api.getHostMode();
    }
    if (!hostUrl || mode === "none") {
      throw new Error("Mac Host Node is offline. Cannot upload files while host is offline.");
    }

    const headers = authHeaders(true);
    delete headers["Content-Type"]; // multipart boundary set by browser
    const formData = new FormData();
    formData.append("file", file);

    const q = directory ? `?directory=${encodeURIComponent(directory)}` : "";
    const res = await fetch(`${hostUrl}/api/files/upload${q}`, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`${res.status}: ${err}`);
    }
    return (await res.json()) as FileItem;
  },

  async downloadFile(path: string, filename: string): Promise<void> {
    const hostUrl = api.getHostUrl();
    if (!hostUrl || api.getHostMode() === "none") {
      throw new Error("Mac Host Node is offline.");
    }
    const res = await fetch(`${hostUrl}/api/files/download?path=${encodeURIComponent(path)}`, {
      method: "GET",
      headers: authHeaders(true),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`${res.status}: ${err}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  async deleteFile(path: string): Promise<void> {
    const q = `?path=${encodeURIComponent(path)}`;
    return hostRequest(`/api/files/delete${q}`, { method: "DELETE" });
  },

  // --- Devices & Nodes ---
  async listDevices(): Promise<Device[]> {
    return hostRequest<Device[]>("/api/devices").catch(() => rawRequest<Device[]>("/api/devices"));
  },

  async getActiveNode(): Promise<ActiveNode | null> {
    try {
      return await rawRequest<ActiveNode>("/api/nodes/active", undefined, CLOUD_BASE, false);
    } catch {
      return null;
    }
  },

  async activity(limit = 30): Promise<ActivityItem[]> {
    return hostRequest(`/api/activity?limit=${limit}`);
  },
};
