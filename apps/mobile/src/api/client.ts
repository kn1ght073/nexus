import { getSecureItem, setSecureItem, deleteSecureItem } from '../utils/secureStore';

export const DEFAULT_SERVER_URL = 'https://nexus-control-plane-uvi8.onrender.com';
const SERVER_URL_KEY = 'nexus_server_url';
const HOST_URL_KEY = 'nexus_host_url';
const HOST_TOKEN_KEY = 'nexus_host_token';
const LAST_SYNC_KEY = 'nexus_last_sync_timestamp';
const ACCESS_TOKEN_KEY = 'nexus_access_token';
const REFRESH_TOKEN_KEY = 'nexus_refresh_token';

let activeServerUrl = DEFAULT_SERVER_URL;
let activeHostUrl: string | null = null;
let activeHostToken: string | null = null;
let activeAccessToken: string | null = null;
let activeRefreshToken: string | null = null;

export async function initApiClient(): Promise<{ serverUrl: string; hostUrl: string | null; hasToken: boolean }> {
  const storedUrl = await getSecureItem(SERVER_URL_KEY);
  if (storedUrl) {
    activeServerUrl = storedUrl.trim().replace(/\/+$/, '');
  }
  const storedHost = await getSecureItem(HOST_URL_KEY);
  if (storedHost) {
    activeHostUrl = storedHost.trim().replace(/\/+$/, '');
  }
  activeHostToken = await getSecureItem(HOST_TOKEN_KEY);
  activeAccessToken = await getSecureItem(ACCESS_TOKEN_KEY);
  activeRefreshToken = await getSecureItem(REFRESH_TOKEN_KEY);

  return {
    serverUrl: activeServerUrl,
    hostUrl: activeHostUrl,
    hasToken: Boolean(activeAccessToken || activeHostToken),
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

export function getHostUrl(): string | null {
  return activeHostUrl;
}

export function getHostToken(): string | null {
  return activeHostToken;
}

export async function setHostToken(token: string | null): Promise<void> {
  activeHostToken = token;
  if (token) {
    await setSecureItem(HOST_TOKEN_KEY, token);
  } else {
    await deleteSecureItem(HOST_TOKEN_KEY);
  }
}

export async function setHostUrl(url: string | null): Promise<void> {
  if (url) {
    const normalized = url.trim().replace(/\/+$/, '');
    activeHostUrl = normalized;
    await setSecureItem(HOST_URL_KEY, normalized);
  } else {
    activeHostUrl = null;
    activeHostToken = null;
    await deleteSecureItem(HOST_URL_KEY);
    await deleteSecureItem(HOST_TOKEN_KEY);
  }
}

export async function exchangeCpTokenOnHost(hostUrl: string, cpToken: string): Promise<string | null> {
  try {
    const norm = hostUrl.trim().replace(/\/+$/, '');
    const res = await fetch(`${norm}/api/auth/cp-exchange`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${cpToken}`,
      },
      body: JSON.stringify({ token: cpToken }),
    });
    if (!res.ok) return null;
    const data = await res.json().catch(() => null);
    if (data?.access_token) {
      await setHostToken(data.access_token);
      return data.access_token;
    }
  } catch (err) {
    console.warn('[ApiClient] Failed to exchange CP token on host:', err);
  }
  return null;
}

export async function autoDiscoverHost(): Promise<{
  discovered: boolean;
  activeHostUrl: string | null;
  mode: 'lan' | 'relay' | 'none';
  node?: any;
}> {
  if (!activeAccessToken) {
    return { discovered: false, activeHostUrl: null, mode: 'none' };
  }

  const fallbackToSavedHost = async (): Promise<{
    discovered: boolean;
    activeHostUrl: string | null;
    mode: 'lan' | 'relay' | 'none';
  }> => {
    const candidateHost = activeHostUrl || (await getSecureItem(HOST_URL_KEY));
    if (candidateHost) {
      const probe = await testConnection(candidateHost);
      if (probe.ok) {
        await setHostUrl(candidateHost);
        await exchangeCpTokenOnHost(candidateHost, activeAccessToken!);
        return { discovered: true, activeHostUrl: candidateHost, mode: 'lan' };
      }
    }
    return { discovered: false, activeHostUrl: null, mode: 'none' };
  };

  try {
    const res = await fetch(`${activeServerUrl}/api/nodes/active`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${activeAccessToken}`,
      },
    });
    if (!res.ok) {
      return await fallbackToSavedHost();
    }
    const node = await res.json().catch(() => null);
    if (!node || !node.id) {
      return await fallbackToSavedHost();
    }

    const lanUrl = node.lan_url || node.endpoint;
    const proxyUrl = node.relay_proxy_url
      ? (node.relay_proxy_url.startsWith('http') ? node.relay_proxy_url : `${activeServerUrl}${node.relay_proxy_url}`)
      : `${activeServerUrl}/api/relay/proxy`;

    // 1. Fast probe local LAN address first (zero cloud latency)
    if (lanUrl && typeof lanUrl === 'string' && lanUrl.startsWith('http')) {
      const probe = await testConnection(lanUrl);
      if (probe.ok) {
        await setHostUrl(lanUrl);
        await exchangeCpTokenOnHost(lanUrl, activeAccessToken);
        return { discovered: true, activeHostUrl: lanUrl, mode: 'lan', node };
      }
    }

    // 2. Global route fallback via encrypted control-plane relay
    await setHostUrl(proxyUrl);
    await exchangeCpTokenOnHost(proxyUrl, activeAccessToken);
    return { discovered: true, activeHostUrl: proxyUrl, mode: 'relay', node };
  } catch (err) {
    console.warn('[ApiClient] Automatic host discovery error:', err);
    return await fallbackToSavedHost();
  }
}

export async function getLastSyncTimestamp(): Promise<string | null> {
  return await getSecureItem(LAST_SYNC_KEY);
}

export async function setLastSyncTimestamp(isoStr: string): Promise<void> {
  await setSecureItem(LAST_SYNC_KEY, isoStr);
}

export async function testConnection(targetUrl: string): Promise<{
  ok: boolean;
  status?: string;
  mode?: string;
  service?: string;
  latencyMs: number;
  error?: string;
}> {
  const t0 = Date.now();
  const normalized = targetUrl.trim().replace(/\/+$/, '');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4000);
  try {
    const res = await fetch(`${normalized}/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(timer);
    const latencyMs = Date.now() - t0;
    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      return {
        ok: true,
        status: data.status || 'ok',
        mode: data.mode || 'unknown',
        service: data.service || 'nexus-core',
        latencyMs,
      };
    }
    return {
      ok: false,
      latencyMs,
      error: `HTTP ${res.status}: ${res.statusText}`,
    };
  } catch (err: any) {
    clearTimeout(timer);
    return {
      ok: false,
      latencyMs: Date.now() - t0,
      error: err.name === 'AbortError' ? 'Connection timed out (4s)' : err.message,
    };
  }
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
  activeHostToken = null;
  await deleteSecureItem(ACCESS_TOKEN_KEY);
  await deleteSecureItem(REFRESH_TOKEN_KEY);
  await deleteSecureItem(HOST_TOKEN_KEY);
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
  
  // Route personal workspace endpoints to authoritative local Host if configured
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const isPersonalDataRoute = cleanPath.startsWith('/api/projects') ||
                              cleanPath.startsWith('/api/tasks') ||
                              cleanPath.startsWith('/api/notes') ||
                              cleanPath.startsWith('/api/files') ||
                              cleanPath.startsWith('/api/sync') ||
                              cleanPath.startsWith('/api/host') ||
                              cleanPath.startsWith('/api/account/overview');

  const isHostTarget = Boolean(isPersonalDataRoute && activeHostUrl);
  const baseUrl = isHostTarget ? activeHostUrl! : activeServerUrl;
  const fullUrl = `${baseUrl}${cleanPath}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  const tokenToUse = isHostTarget ? (activeHostToken || activeAccessToken) : activeAccessToken;
  if (tokenToUse) {
    headers['Authorization'] = `Bearer ${tokenToUse}`;
  }
  if (isHostTarget && activeHostToken && activeAccessToken && activeAccessToken !== activeHostToken) {
    headers['X-Nexus-Node-Authorization'] = `Bearer ${activeHostToken}`;
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

    if (response.status === 401 && isHostTarget && activeAccessToken) {
      const exchanged = await exchangeCpTokenOnHost(activeHostUrl!, activeAccessToken);
      if (exchanged) {
        return apiClient<T>(path, options);
      }
    }

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
