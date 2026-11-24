import {
  setServerUrl,
  getServerUrl,
  saveAuthTokens,
  getAccessToken,
  clearAuthTokens,
  DEFAULT_SERVER_URL,
} from '../src/api/client';

describe('NEXUS Mobile ApiClient & Token Handling', () => {
  beforeEach(async () => {
    await clearAuthTokens();
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

    await clearAuthTokens();
    expect(getAccessToken()).toBeNull();
  });
});
