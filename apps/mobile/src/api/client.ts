import { getSecureItem, setSecureItem, deleteSecureItem } from '../utils/secureStore';

export const DEFAULT_SERVER_URL = 'https://nexus-control-plane-uvi8.onrender.com';
const SERVER_URL_KEY = 'nexus_server_url';
const ACCESS_TOKEN_KEY = 'nexus_access_token';
const REFRESH_TOKEN_KEY = 'nexus_refresh_token';

let activeServerUrl = DEFAULT_SERVER_URL;
let activeAccessToken: string | null = null;
let activeRefreshToken: string | null = null;

export async function initApiClient(): Promise<{ serverUrl: string; hasToken: boolean }> {
  const storedUrl = await getSecureItem(SERVER_URL_KEY);
  if (storedUrl) {
    activeServerUrl = storedUrl.trim().replace(/\/+$/, '');
  }
  activeAccessToken = await getSecureItem(ACCESS_TOKEN_KEY);
  activeRefreshToken = await getSecureItem(REFRESH_TOKEN_KEY);

  return {
    serverUrl: activeServerUrl,
    hasToken: Boolean(activeAccessToken),
  };
}

export function getServerUrl(): string {
  return activeServerUrl;
}

export async function setServerUrl(url: string): Promise<void> {
  const normalized = url.trim().replace(/\/+$/, '');
  activeServerUrl = normalized;
  await setSecureItem(SERVER_URL_KEY, normalized);
}

export function getAccessToken(): string | null {
  return activeAccessToken;
}

export async function saveAuthTokens(access: string, refresh: string): Promise<void> {
  activeAccessToken = access;
  activeRefreshToken = refresh;
  await setSecureItem(ACCESS_TOKEN_KEY, access);
  await setSecureItem(REFRESH_TOKEN_KEY, refresh);
}

export async function clearAuthTokens(): Promise<void> {
  activeAccessToken = null;
  activeRefreshToken = null;
  await deleteSecureItem(ACCESS_TOKEN_KEY);
  await deleteSecureItem(REFRESH_TOKEN_KEY);
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function apiClient<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 15000, ...fetchOpts } = options;
  const fullUrl = `${activeServerUrl}${path.startsWith('/') ? path : `/${path}`}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (activeAccessToken) {
    headers['Authorization'] = `Bearer ${activeAccessToken}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(fullUrl, {
      ...fetchOpts,
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (response.status === 401 && activeRefreshToken && !path.includes('/auth/refresh')) {
      const refreshed = await tryRefreshToken();
      if (refreshed) {
        return apiClient<T>(path, options);
      }
    }

    if (response.status === 204) {
      return null as unknown as T;
    }

    const json = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMsg = extractErrorMessage(json.detail, response.status);
      throw new ApiError(errorMsg, response.status, json);
    }

    return json as T;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out', 408);
    }
    throw err;
  }
}

function extractErrorMessage(detail: any, status: number): string {
  if (!detail) return `Request failed with status ${status}`;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => {
      if (typeof d === 'string') return d;
      const field = Array.isArray(d.loc) ? d.loc.filter((l: any) => l !== 'body').join('.') : '';
      return field ? `${field}: ${d.msg || JSON.stringify(d)}` : (d.msg || JSON.stringify(d));
    }).join('; ');
  }
  if (typeof detail === 'object') {
    return detail.message || detail.msg || JSON.stringify(detail);
  }
  return String(detail);
}

async function tryRefreshToken(): Promise<boolean> {
  if (!activeRefreshToken) return false;
  try {
    const res = await fetch(`${activeServerUrl}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: activeRefreshToken }),
    });

    if (res.ok) {
      const tokens = await res.json();
      await saveAuthTokens(tokens.access_token, tokens.refresh_token);
      return true;
    }
  } catch (e) {
    console.warn('[ApiClient] Failed to refresh token:', e);
  }
  await clearAuthTokens();
  return false;
}
