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

(async () => {
  const origFetch = globalThis.fetch;

  // Test 5: loginWithToken - cloud token automatically discovers local node via cp-exchange
  api.clearToken();
  api.setBaseUrl("http://127.0.0.1:8000");
  globalThis.fetch = async (url: any) => {
    const sUrl = String(url);
    if (sUrl === "http://127.0.0.1:8000/api/auth/me") {
      return { ok: false, status: 401, text: async () => '{"detail":"Invalid or expired token"}' } as any;
    }
    if (sUrl === "https://nexus-control-plane-uvi8.onrender.com/api/auth/me") {
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 2, email: "operator@cloud.com", created_at: "2026-01-01" }),
      } as any;
    }
    if (sUrl === "http://127.0.0.1:8000/health") {
      return {
        ok: true,
        status: 200,
        json: async () => ({ status: "ok", service: "nexus-core", mode: "node" }),
      } as any;
    }
    if (sUrl === "http://127.0.0.1:8000/api/auth/cp-exchange") {
      return {
        ok: true,
        status: 200,
        json: async () => ({ access_token: "local-exchanged-jwt", refresh_token: "r" }),
      } as any;
    }
    if (sUrl === "http://127.0.0.1:8000/api/projects") {
      return {
        ok: true,
        status: 200,
        json: async () => [{ id: 1, title: "Local SQLite Project", description: null, status: "pending", revision: 1, created_at: "2026-01-01", updated_at: "2026-01-01" }],
      } as any;
    }
    throw new Error("Unexpected URL: " + sUrl);
  };

  const userCloud = await api.loginWithToken("cloud-jwt-token");
  assert.strictEqual(userCloud.email, "operator@cloud.com");
  assert.strictEqual(api.getHostMode(), "local");
  assert.strictEqual(api.getHostUrl(), "http://127.0.0.1:8000");
  assert.strictEqual(api.getHostToken(), "local-exchanged-jwt");
  const projs = await api.listProjects();
  assert.strictEqual(projs[0].title, "Local SQLite Project");
  console.log("✓ cloud login + cp-exchange to local Mac host test passed");

  // Test 6: relay mode routes data endpoints through /api/relay/{id}/proxy with dual headers
  api.clearToken();
  api.setBaseUrl("https://nexus-control-plane-uvi8.onrender.com");
  let capturedRelayHeaders: Record<string, string> = {};
  globalThis.fetch = async (url: any, init?: any) => {
    const sUrl = String(url);
    if (sUrl === "https://nexus-control-plane-uvi8.onrender.com/api/auth/me") {
      return { ok: true, status: 200, json: async () => ({ id: 2, email: "operator@cloud.com", created_at: "2026-01-01" }) } as any;
    }
    if (sUrl === "http://127.0.0.1:8000/health") {
      throw new Error("ECONNREFUSED");
    }
    if (sUrl === "https://nexus-control-plane-uvi8.onrender.com/api/nodes/active") {
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 7, name: "MacBook", is_active: true, lan_url: "http://10.0.0.5:8000", relay_proxy_url: "/api/relay/7/proxy" }),
      } as any;
    }
    if (sUrl === "http://10.0.0.5:8000/health") {
      throw new Error("LAN unreachable");
    }
    if (sUrl === "https://nexus-control-plane-uvi8.onrender.com/api/relay/7/proxy/api/auth/cp-exchange") {
      return { ok: true, status: 200, json: async () => ({ access_token: "relayed-node-jwt", refresh_token: "r2" }) } as any;
    }
    if (sUrl === "https://nexus-control-plane-uvi8.onrender.com/api/relay/7/proxy/api/projects") {
      capturedRelayHeaders = init?.headers ?? {};
      return { ok: true, status: 200, json: async () => [] } as any;
    }
    throw new Error("Unexpected URL: " + sUrl);
  };

  await api.loginWithToken("cloud-jwt-token");
  assert.strictEqual(api.getHostMode(), "relay");
  assert.strictEqual(api.getHostUrl(), "https://nexus-control-plane-uvi8.onrender.com/api/relay/7/proxy");
  await api.listProjects();
  assert.strictEqual(capturedRelayHeaders["Authorization"], "Bearer cloud-jwt-token");
  assert.strictEqual(capturedRelayHeaders["X-Nexus-Node-Authorization"], "Bearer relayed-node-jwt");
  console.log("✓ relay fallback proxy + dual auth header test passed");

  // Test 7: offline host never hits control-plane /api/projects (no 404 Not Found)
  api.clearToken();
  api.setBaseUrl("https://nexus-control-plane-uvi8.onrender.com");
  globalThis.fetch = async (url: any) => {
    const sUrl = String(url);
    if (sUrl === "https://nexus-control-plane-uvi8.onrender.com/api/auth/me") {
      return { ok: true, status: 200, json: async () => ({ id: 2, email: "operator@cloud.com", created_at: "2026-01-01" }) } as any;
    }
    if (sUrl === "http://127.0.0.1:8000/health") {
      throw new Error("ECONNREFUSED");
    }
    if (sUrl === "https://nexus-control-plane-uvi8.onrender.com/api/nodes/active") {
      return { ok: true, status: 200, json: async () => null } as any;
    }
    throw new Error("Should NOT hit URL: " + sUrl);
  };

  await api.loginWithToken("cloud-jwt-token");
  assert.strictEqual(api.getHostMode(), "none");
  let offlineCaught = false;
  try {
    await api.listProjects();
  } catch (e: any) {
    offlineCaught = true;
    assert.match(e.message, /Mac Host Node is offline/);
  }
  assert.strictEqual(offlineCaught, true);
  console.log("✓ offline host blocks 404 control-plane calls cleanly");

  // Test 8: bad token on all endpoints clears token and throws
  api.clearToken();
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

  globalThis.fetch = origFetch;
  console.log("ALL 8 DESKTOP API TESTS PASSED SUCCESSFULLY!");
})();
