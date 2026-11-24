// Unit tests for NEXUS Desktop API client

import assert from "node:assert";
import { api, cleanToken, normalizeBaseUrl } from "./api.ts";

// Mock localStorage for Node test environment
const mockStorage: Record<string, string> = {};
(globalThis as any).localStorage = {
  getItem: (k: string) => mockStorage[k] ?? null,
  setItem: (k: string, v: string) => { mockStorage[k] = v; },
  removeItem: (k: string) => { delete mockStorage[k]; },
  clear: () => {
    for (const k of Object.keys(mockStorage)) delete mockStorage[k];
  },
};

console.log("Running desktop API unit tests...");

// Test 1: cleanToken
assert.strictEqual(cleanToken("eyJhbGciOi..."), "eyJhbGciOi...");
assert.strictEqual(cleanToken("  Bearer eyJhbGciOi...  "), "eyJhbGciOi...");
assert.strictEqual(cleanToken("bearer eyJhbGciOi..."), "eyJhbGciOi...");
assert.strictEqual(cleanToken('"eyJhbGciOi..."'), "eyJhbGciOi...");
assert.strictEqual(cleanToken("'eyJhbGciOi...'"), "eyJhbGciOi...");
assert.strictEqual(cleanToken('  "Bearer eyJhbGciOi..."  '), "Bearer eyJhbGciOi...");
assert.strictEqual(cleanToken(cleanToken('  "Bearer eyJhbGciOi..."  ')), "eyJhbGciOi...");
assert.strictEqual(cleanToken(""), "");
console.log("✓ cleanToken tests passed");

// Test 2: normalizeBaseUrl
assert.strictEqual(normalizeBaseUrl("http://127.0.0.1:8000/"), "http://127.0.0.1:8000");
assert.strictEqual(normalizeBaseUrl("https://nexus-control-plane-uvi8.onrender.com///"), "https://nexus-control-plane-uvi8.onrender.com");
assert.strictEqual(normalizeBaseUrl("  http://localhost:8000/  "), "http://localhost:8000");
assert.strictEqual(normalizeBaseUrl(""), "");
console.log("✓ normalizeBaseUrl tests passed");

// Test 3: isLocalUrl and isCloudUrl
assert.strictEqual(api.isLocalUrl("http://127.0.0.1:8000"), true);
assert.strictEqual(api.isLocalUrl("http://127.0.0.1:8000/"), true);
assert.strictEqual(api.isLocalUrl("http://localhost:8000/"), true);
assert.strictEqual(api.isLocalUrl("https://nexus-control-plane-uvi8.onrender.com"), false);

assert.strictEqual(api.isCloudUrl("https://nexus-control-plane-uvi8.onrender.com"), true);
assert.strictEqual(api.isCloudUrl("https://nexus-control-plane-uvi8.onrender.com/"), true);
assert.strictEqual(api.isCloudUrl("http://127.0.0.1:8000"), false);
console.log("✓ isLocalUrl and isCloudUrl tests passed");

// Test 4: setBaseUrl / getBaseUrl
api.setBaseUrl("http://127.0.0.1:8000/");
assert.strictEqual(api.getBaseUrl(), "http://127.0.0.1:8000");
api.setBaseUrl("https://nexus-control-plane-uvi8.onrender.com///");
assert.strictEqual(api.getBaseUrl(), "https://nexus-control-plane-uvi8.onrender.com");
console.log("✓ setBaseUrl / getBaseUrl normalization tests passed");

// Test 5: loginWithToken - primary success
(async () => {
  api.setBaseUrl("http://127.0.0.1:8000");
  const origFetch = globalThis.fetch;

  // Mock fetch returning success for primary
  globalThis.fetch = async (url: any) => {
    const sUrl = String(url);
    if (sUrl.startsWith("http://127.0.0.1:8000/api/auth/me")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 1, email: "local@nexus.local", created_at: "2026-01-01" }),
      } as any;
    }
    throw new Error("Unexpected URL: " + sUrl);
  };

  const user = await api.loginWithToken("  Bearer test-token-1  ");
  assert.strictEqual(user.email, "local@nexus.local");
  assert.strictEqual(api.getToken(), "test-token-1");
  assert.strictEqual(api.getBaseUrl(), "http://127.0.0.1:8000");
  console.log("✓ loginWithToken primary success test passed");

  // Test 6: loginWithToken - local fails, cloud fallback succeeds
  api.setBaseUrl("http://127.0.0.1:8000");
  globalThis.fetch = async (url: any) => {
    const sUrl = String(url);
    if (sUrl.startsWith("http://127.0.0.1:8000/api/auth/me")) {
      return {
        ok: false,
        status: 401,
        text: async () => '{"detail":"Signature verification failed"}',
      } as any;
    }
    if (sUrl.startsWith("https://nexus-control-plane-uvi8.onrender.com/api/auth/me")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 2, email: "operator@cloud.com", created_at: "2026-01-01" }),
      } as any;
    }
    throw new Error("Unexpected URL: " + sUrl);
  };

  const userCloud = await api.loginWithToken("cloud-jwt-token");
  assert.strictEqual(userCloud.email, "operator@cloud.com");
  assert.strictEqual(api.getBaseUrl(), "https://nexus-control-plane-uvi8.onrender.com");
  console.log("✓ loginWithToken fallback to cloud test passed (auto-switched base URL)");

  // Test 7: loginWithToken - cloud fails, local fallback succeeds
  api.setBaseUrl("https://nexus-control-plane-uvi8.onrender.com");
  globalThis.fetch = async (url: any) => {
    const sUrl = String(url);
    if (sUrl.startsWith("https://nexus-control-plane-uvi8.onrender.com/api/auth/me")) {
      return {
        ok: false,
        status: 401,
        text: async () => '{"detail":"Invalid token"}',
      } as any;
    }
    if (sUrl.startsWith("http://127.0.0.1:8000/api/auth/me")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 3, email: "dev@nexus.local", created_at: "2026-01-01" }),
      } as any;
    }
    throw new Error("Unexpected URL: " + sUrl);
  };

  const userLocal = await api.loginWithToken("local-jwt-token");
  assert.strictEqual(userLocal.email, "dev@nexus.local");
  assert.strictEqual(api.getBaseUrl(), "http://127.0.0.1:8000");
  console.log("✓ loginWithToken fallback to local test passed (auto-switched base URL)");

  // Test 8: loginWithToken - both fail (token cleared, error thrown)
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    text: async () => '{"detail":"Invalid token on all endpoints"}',
  } as any);

  let caught = false;
  try {
    await api.loginWithToken("bad-token");
  } catch (e: any) {
    caught = true;
    assert.match(e.message, /Auth failed/);
  }
  assert.strictEqual(caught, true);
  assert.strictEqual(api.hasToken(), false);
  console.log("✓ loginWithToken failure clears token and throws test passed");

  // Restore fetch
  globalThis.fetch = origFetch;
  console.log("ALL 8 DESKTOP API TESTS PASSED SUCCESSFULLY!");
})();
