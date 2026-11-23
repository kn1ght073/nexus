/**
 * Central Server-Side API Client for NEXUS Core API
 * Communicates strictly with FastAPI backend using NEXUS_API_BASE_URL.
 * Keeps tokens out of client-side JavaScript by storing them in HttpOnly Secure cookies.
 */
import { cookies } from "next/headers";
import {
  User,
  SystemStatus,
  NodeRecord,
  DeviceRecord,
  ActivityRecord,
  SessionRecord,
  RelayStatus,
  ServiceStatusResponse,
  PackagesResponse,
} from "./types";

const getBaseUrl = () => {
  return (process.env.NEXUS_API_BASE_URL || "https://nexus-control-plane-uvi8.onrender.com").replace(/\/$/, "");
};

export async function serverApiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<{ data: T | null; error: string | null; status: number }> {
  const baseUrl = getBaseUrl();
  const cookieStore = await cookies();
  const token = cookieStore.get("nexus_access_token")?.value;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers,
      cache: "no-store",
    });

    if (res.status === 204) {
      return { data: null, error: null, status: res.status };
    }

    if (!res.ok) {
      const text = await res.text();
      let errorMsg = text;
      try {
        const j = JSON.parse(text);
        errorMsg = j.detail || text;
      } catch {}
      return { data: null, error: errorMsg, status: res.status };
    }

    const data = await res.json();
    return { data, error: null, status: res.status };
  } catch (err: any) {
    return { data: null, error: err.message || "Failed to connect to NEXUS Core API", status: 503 };
  }
}

export const coreApi = {
  async getHealth() {
    return serverApiFetch<{ status: string; service: string; mode: string }>("/health");
  },

  async getCurrentUser() {
    return serverApiFetch<User>("/api/auth/me");
  },

  async getSystemStatus() {
    return serverApiFetch<SystemStatus>("/api/system/status");
  },

  async getNodes() {
    return serverApiFetch<NodeRecord[]>("/api/nodes");
  },

  async getDevices() {
    return serverApiFetch<DeviceRecord[]>("/api/devices");
  },

  async getActivity(limit = 50) {
    return serverApiFetch<ActivityRecord[]>(`/api/activity?limit=${limit}`);
  },

  async getSessions() {
    return serverApiFetch<SessionRecord[]>("/api/auth/sessions");
  },

  async getRelayStatus() {
    return serverApiFetch<RelayStatus>("/api/relay/status");
  },

  async revokeSession(sessionId: number) {
    return serverApiFetch<{ ok: boolean; detail: string }>(`/api/auth/sessions/${sessionId}`, {
      method: "DELETE",
    });
  },

  async logout(refreshToken?: string) {
    return serverApiFetch<{ ok: boolean }>("/api/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  async getUsers() {
    return serverApiFetch<User[]>("/api/auth/users");
  },

  async updateUserRole(userId: number, role: "user" | "operator" | "owner") {
    return serverApiFetch<User>(`/api/auth/users/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
  },

  async getServiceStatus() {
    return serverApiFetch<ServiceStatusResponse>("/api/services/status");
  },

  async getPackages(mirror?: string) {
    const q = mirror ? `?mirror=${encodeURIComponent(mirror)}` : "";
    return serverApiFetch<PackagesResponse>(`/api/services/packages${q}`);
  },

  async registerDevice(payload: { name: string; platform: string; capabilities: string[] }) {
    return serverApiFetch<DeviceRecord>("/api/devices/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async removeDevice(deviceId: number) {
    return serverApiFetch<void>(`/api/devices/${deviceId}`, {
      method: "DELETE",
    });
  },

  async claimNode(payload: { name: string; platform: string; endpoint?: string }) {
    return serverApiFetch<NodeRecord>("/api/nodes/claim", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // --- Client Console APIs ---
  async getAccountOverview() {
    return serverApiFetch<import("./types").AccountOverview>("/api/account/overview");
  },

  async getAccountDevices() {
    return serverApiFetch<DeviceRecord[]>("/api/account/devices");
  },

  async revokeAccountDevice(deviceId: number) {
    return serverApiFetch<void>(`/api/account/devices/${deviceId}`, {
      method: "DELETE",
    });
  },

  async getAccountSessions() {
    return serverApiFetch<SessionRecord[]>("/api/account/sessions");
  },

  async revokeAccountSession(sessionId: number) {
    return serverApiFetch<{ ok: boolean; detail: string }>(`/api/account/sessions/${sessionId}`, {
      method: "DELETE",
    });
  },

  async getAccountActivity(category?: string, limit = 50, offset = 0) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (category && category !== "all") params.set("category", category);
    return serverApiFetch<import("./types").ActivityPage>(`/api/account/activity?${params.toString()}`);
  },

  async getClientServerStatus() {
    return serverApiFetch<import("./types").ClientServerStatus>("/api/account/server-status");
  },

  async getAccountDataSummary() {
    return serverApiFetch<import("./types").AccountDataSummary>("/api/account/data-summary");
  },
};
