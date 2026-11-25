import {
  setServerUrl,
  getServerUrl,
  setHostUrl,
  getHostUrl,
  saveAuthTokens,
  getAccessToken,
  getHostToken,
  setHostToken,
  clearAuthTokens,
  autoDiscoverHost,
  apiClient,
  DEFAULT_SERVER_URL,
} from '../src/api/client';

describe('NEXUS Mobile ApiClient & Token Handling', () => {
  const originalFetch = global.fetch;

  beforeEach(async () => {
    await clearAuthTokens();
    await setHostUrl(null);
    await setServerUrl(DEFAULT_SERVER_URL);
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  test('defaults to live control plane endpoint', () => {
    expect(getServerUrl()).toBe(DEFAULT_SERVER_URL);
  });

  test('normalizes custom server URLs without trailing slash', async () => {
    await setServerUrl('https://custom.nexus.local:8443///');
    expect(getServerUrl()).toBe('https://custom.nexus.local:8443');
  });

  test('stores and purges authentication tokens securely', async () => {
    expect(getAccessToken()).toBeNull();
    await saveAuthTokens('jwt_access_123', 'jwt_refresh_456');
    expect(getAccessToken()).toBe('jwt_access_123');

    await setHostToken('node_host_token_789');
    expect(getHostToken()).toBe('node_host_token_789');

    await clearAuthTokens();
    expect(getAccessToken()).toBeNull();
    expect(getHostToken()).toBeNull();
  });

  test('autoDiscoverHost falls back to testing activeHostUrl when control plane returns no node', async () => {
    await saveAuthTokens('jwt_access_123', 'jwt_refresh_456');
    await setHostUrl('http://10.7.31.71:8000');

    global.fetch = jest.fn((url: string) => {
      if (url.includes('/api/nodes/active')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ id: null }),
        } as any);
      }
      if (url.includes('/health')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: 'ok', mode: 'edge-node' }),
        } as any);
      }
      if (url.includes('/api/auth/cp-exchange')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ access_token: 'host_token_xyz' }),
        } as any);
      }
      return Promise.reject(new Error(`Unexpected fetch url: ${url}`));
    }) as any;

    const res = await autoDiscoverHost();
    expect(res.discovered).toBe(true);
    expect(res.activeHostUrl).toBe('http://10.7.31.71:8000');
    expect(res.mode).toBe('lan');
    expect(getHostToken()).toBe('host_token_xyz');
  });

  test('routes /api/account/overview to activeHostUrl when host is configured', async () => {
    await saveAuthTokens('jwt_access_123', 'jwt_refresh_456');
    await setHostUrl('http://10.7.31.71:8000');

    let requestedUrl = '';
    global.fetch = jest.fn((url: string) => {
      requestedUrl = url;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 1, email: 'user@example.com', metrics: { projects: 2 } }),
      } as any);
    }) as any;

    const res = await apiClient<any>('/api/account/overview');
    expect(requestedUrl).toBe('http://10.7.31.71:8000/api/account/overview');
    expect(res.metrics.projects).toBe(2);
  });
});
