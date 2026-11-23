/**
 * NEXUS Core API client (frontend half).
 *
 * All calls go to the NEXUS Core REST API. The token is kept in
 * localStorage for the skeleton; the production plan is the OS keychain via
 * the Tauri stronghold/keyring plugin (progress.md step 4).
 */

const BASE = localStorage.getItem("nexus.core") ?? "https://nexus-control-plane-uvi8.onrender.com";

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
  updated_at: string;
}

export interface Device {
  id: number;
  name: string;
  platform: string;
  capabilities: string[];
  is_online: boolean;
}

function headers(): Record<string, string> {
  const token = localStorage.getItem("nexus.token");
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
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
  baseUrl: BASE,

  setToken(token: string) {
    localStorage.setItem("nexus.token", token);
  },
  clearToken() {
    localStorage.removeItem("nexus.token");
  },
  hasToken(): boolean {
    return localStorage.getItem("nexus.token") !== null;
  },

  async health(): Promise<{ status: string; service: string; version: string }> {
    return request("/health");
  },

  async login(email: string, password: string): Promise<{ access_token: string; refresh_token: string }> {
    return request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  async register(email: string, password: string): Promise<User> {
    return request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  async me(): Promise<User> {
    return request("/api/auth/me");
  },

  async listProjects(): Promise<Project[]> {
    return request("/api/projects");
  },

  async createProject(title: string, description: string): Promise<Project> {
    return request("/api/projects", {
      method: "POST",
      body: JSON.stringify({ title, description }),
    });
  },

  async listTasks(): Promise<Task[]> {
    return request("/api/tasks");
  },

  async createTask(title: string, projectId?: number): Promise<Task> {
    return request("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ title, project_id: projectId ?? null }),
    });
  },

  async completeTask(taskId: number): Promise<Task> {
    return request(`/api/tasks/${taskId}/done`, { method: "POST" });
  },

  async listDevices(): Promise<Device[]> {
    return request("/api/devices");
  },

  async activity(limit = 20): Promise<Array<{ id: number; action: string; detail: string; created_at: string }>> {
    return request(`/api/activity?limit=${limit}`);
  },
};
