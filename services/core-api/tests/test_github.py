"""GitHub linking + highlights — tests with a local GitHub stub.

The stub emulates the four real endpoints the router talks to
(docs.github.com, "Authorizing OAuth apps"):
  POST /login/device/code                (device flow start)
  POST /login/oauth/access_token         (device poll + authorize exchange)
  GET  /login/oauth/authorize            (authorize-url shape check, URL only)
  GET  /api.github.com/*                  (user, repos, events)

The router's settings are pointed at the stub through NEXUS_GITHUB_*
env vars, so the tests exercise the EXACT code paths production uses.
"""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from nexus_core.settings import get_settings

# ---------------------------------------------------------------------------
# A tiny GitHub stub


class _StubHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def _json(self, code, body, headers=None):
        import json as _j

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            self.send_header(k, str(v))
        payload = _j.dumps(body).encode() if body is not None else b""
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        import json as _j

        body = _j.loads(self.rfile.read(length) or b"{}") if length else {}

        if self.path == "/login/device/code":
            # Accept: application/json demanded by the docs
            assert "application/json" in self.headers.get("Accept", ""), "device/code needs JSON Accept"
            state = _StubHandler.scenario
            if state == "device_start_error":
                self._json(500, {})
                return
            self._json(200, {
                "device_code": "dc-123",
                "user_code": "ABCD-1234",
                "verification_uri": "https://github.com/login/device",
                "expires_in": 900,
                "interval": 5,
            })
            return

        if self.path == "/login/oauth/access_token":
            state = _StubHandler.scenario
            if state == "pending":
                self._json(200, {"error": "authorization_pending"})
                return
            if state == "slow_down":
                self._json(200, {"error": "slow_down"})
                return
            if state == "denied":
                self._json(200, {"error": "access_denied"})
                return
            if state == "expired":
                self._json(200, {"error": "expired_token"})
                return
            if state == "authorize_bad_code":
                self._json(200, {"error": "bad_verification_code"})
                return
            if state == "authorize_ok":
                # Real GitHub echoes granted scopes in this header
                self._json(200, {"access_token": "gho_stubtoken", "token_type": "bearer"},
                           headers={"X-OAuth-Scopes": "read:user"})
                return
            # default: device-flow success
            self._json(200, {"access_token": "gho_stubtoken", "token_type": "bearer"},
                       headers={"X-OAuth-Scopes": "read:user"})
            return

        self._json(404, {"message": "not found"})

    def do_GET(self):
        # NB: /users/... must be matched before /user (prefix overlap)
        if self.path.startswith("/users/octocat/repos"):
            self._json(200, [
                {
                    "name": "Spoon-Knife",
                    "stargazers_count": 12345,
                    "language": "HTML",
                    "description": "This repo is for demonstration purposes only.",
                    "html_url": "https://github.com/octocat/Spoon-Knife",
                    "pushed_at": "2026-11-01T10:00:00Z",
                }
            ])
            return
        if self.path.startswith("/users/octocat/events/public"):
            self._json(200, [
                {
                    "type": "PushEvent",
                    "repo": {"name": "octocat/Spoon-Knife"},
                    "created_at": "2026-11-15T10:00:00Z",
                    "payload": {"commits": [{}, {}]},
                },
                {
                    "type": "WatchEvent",
                    "repo": {"name": "cli/cli"},
                    "created_at": "2026-11-14T10:00:00Z",
                    "payload": {},
                },
            ])
            return
        if self.path.startswith("/user"):
            self._json(200, {
                "login": "octocat",
                "id": 583231,
                "name": "The Octocat",
                "avatar_url": "https://avatars.example.com/octocat.png",
                "bio": "Testing",
                "company": "GitHub",
                "location": "SF",
                "public_repos": 8,
                "public_gists": 0,
                "followers": 4200,
                "following": 10,
                "html_url": "https://github.com/octocat",
            }, headers={"X-OAuth-Scopes": "read:user", "X-RateLimit-Remaining": "4999"})
            return
        self._json(404, {"message": "not found"})

    def do_DELETE(self):
        # revocation endpoint — always succeeds like the real one
        self._json(200, {})


_StubHandler.scenario = "ok"

_STUB_PORT = 8931


@pytest.fixture(scope="module")
def github_stub():
    server = HTTPServer(("127.0.0.1", _STUB_PORT), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield _StubHandler
    server.shutdown()


def _configure_stub_env(monkeypatch, github_stub):
    """Point the router's settings at the stub via env + cache clear."""
    base = f"http://127.0.0.1:{_STUB_PORT}"
    monkeypatch.setenv("NEXUS_GITHUB_CLIENT_ID", "stub-client-id")
    monkeypatch.setenv("NEXUS_GITHUB_CLIENT_SECRET", "stub-secret")
    monkeypatch.setenv("NEXUS_GITHUB_LOGIN_BASE", base)
    monkeypatch.setenv("NEXUS_GITHUB_API_BASE", base)
    get_settings.cache_clear()

    # the app holds module-level settings snapshots in the routers; refresh them
    import nexus_core.routers.github as gh_router
    gh_router._settings = get_settings()

    # in-memory session state must not leak between tests
    gh_router._pending_device.clear()
    gh_router._pending_authorize.clear()
    gh_router._highlights_cache.clear()
    return gh_router


def _reset_settings(monkeypatch):
    monkeypatch.delenv("NEXUS_GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("NEXUS_GITHUB_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("NEXUS_GITHUB_LOGIN_BASE", raising=False)
    monkeypatch.delenv("NEXUS_GITHUB_API_BASE", raising=False)
    get_settings.cache_clear()
    import nexus_core.routers.github as gh_router
    gh_router._settings = get_settings()


# ---------------------------------------------------------------------------
# Device flow (gh-CLI pattern)


def test_device_flow_happy_path(client, user_a, github_stub, monkeypatch):
    gh = _configure_stub_env(monkeypatch, github_stub)
    github_stub.scenario = "ok"

    r = client.post("/api/github/device/start", headers=user_a["headers"])
    assert r.status_code == 200, r.text
    start = r.json()
    assert start["user_code"] == "ABCD-1234"
    assert start["verification_uri"] == "https://github.com/login/device"
    assert start["device_code"] == "dc-123"
    assert start["interval"] == 5

    r = client.post("/api/github/device/poll", json={"device_code": start["device_code"]}, headers=user_a["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "linked"
    assert body["profile"]["login"] == "octocat"
    assert body["profile"]["github_id"] == 583231
    assert body["profile"]["scopes"] == "read:user"

    # status reflects the link without exposing the token
    r = client.get("/api/github/status", headers=user_a["headers"])
    assert r.status_code == 200
    assert r.json()["linked"] is True
    assert "gho_stubtoken" not in r.text


def test_device_poll_pending_slow_denied(client, user_a, github_stub, monkeypatch):
    gh = _configure_stub_env(monkeypatch, github_stub)

    r = client.post("/api/github/device/start", headers=user_a["headers"])
    device_code = r.json()["device_code"]

    for scenario, want in (("pending", "pending"), ("slow_down", "slow_down"), ("denied", "denied")):
        github_stub.scenario = scenario
        r = client.post("/api/github/device/poll", json={"device_code": device_code}, headers=user_a["headers"])
        assert r.status_code == 200, r.text
        assert r.json()["status"] == want, f"{scenario}: {r.text}"

    # after denial the code is consumed
    r = client.post("/api/github/device/poll", json={"device_code": device_code}, headers=user_a["headers"])
    assert r.status_code == 404


def test_device_flow_second_user_cannot_hijack(client, user_a, user_b, github_stub, monkeypatch):
    gh = _configure_stub_env(monkeypatch, github_stub)
    github_stub.scenario = "ok"

    r = client.post("/api/github/device/start", headers=user_a["headers"])
    device_code = r.json()["device_code"]
    r = client.post("/api/github/device/poll", json={"device_code": device_code}, headers=user_b["headers"])
    assert r.status_code == 403
    assert r.json()["detail"] == "This device code belongs to another session."


def test_device_start_503_without_config(client, user_a, github_stub, monkeypatch):
    _configure_stub_env(monkeypatch, github_stub)
    monkeypatch.delenv("NEXUS_GITHUB_CLIENT_ID", raising=False)
    get_settings.cache_clear()
    import nexus_core.routers.github as gh_router
    gh_router._settings = get_settings()

    r = client.post("/api/github/device/start", headers=user_a["headers"])
    assert r.status_code == 503
    _reset_settings(monkeypatch)


def test_unknown_device_code_404(client, user_a, github_stub, monkeypatch):
    _configure_stub_env(monkeypatch, github_stub)
    r = client.post("/api/github/device/poll", json={"device_code": "nope"}, headers=user_a["headers"])
    assert r.status_code == 404


def test_auth_required_on_all_github_routes(client, github_stub, monkeypatch):
    _configure_stub_env(monkeypatch, github_stub)
    # valid-shaped bodies so the auth dependency (not validation) is what fails
    bodies = {
        "/api/github/device/start": {"scopes": "read:user"},
        "/api/github/device/poll": {"device_code": "x"},
        "/api/github/authorize/callback": {"code": "x", "state": "y" * 8},
    }
    for method, path in (
        ("post", "/api/github/device/start"),
        ("post", "/api/github/device/poll"),
        ("get", "/api/github/authorize-url"),
        ("post", "/api/github/authorize/callback"),
        ("get", "/api/github/status"),
        ("get", "/api/github/highlights"),
        ("delete", "/api/github/link"),
    ):
        if method == "post":
            r = client.post(path, json=bodies[path])
        else:
            r = getattr(client, method)(path)
        assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


# ---------------------------------------------------------------------------
# Authorize-code flow (desktop app pattern)


def test_authorize_flow_happy_path(client, user_a, github_stub, monkeypatch):
    _configure_stub_env(monkeypatch, github_stub)
    github_stub.scenario = "authorize_ok"

    r = client.get("/api/github/authorize-url", headers=user_a["headers"])
    assert r.status_code == 200, r.text
    url_body = r.json()
    # the login base points at the stub in tests; the PATH + params are what matter
    assert "/login/oauth/authorize" in url_body["url"]
    assert "client_id=stub-client-id" in url_body["url"]
    assert "state=" in url_body["url"]
    assert "scope=read" in url_body["url"]

    # state is single-use: exchange once
    r = client.post(
        "/api/github/authorize/callback",
        json={"code": "abc123", "state": url_body["state"]},
        headers=user_a["headers"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "linked"
    assert r.json()["profile"]["login"] == "octocat"

    # replaying the same state must fail
    r = client.post(
        "/api/github/authorize/callback",
        json={"code": "abc123", "state": url_body["state"]},
        headers=user_a["headers"],
    )
    assert r.status_code == 400


def test_authorize_state_bound_to_user(client, user_a, user_b, github_stub, monkeypatch):
    _configure_stub_env(monkeypatch, github_stub)
    github_stub.scenario = "authorize_ok"
    r = client.get("/api/github/authorize-url", headers=user_a["headers"])
    state = r.json()["state"]
    r = client.post(
        "/api/github/authorize/callback", json={"code": "c", "state": state}, headers=user_b["headers"]
    )
    assert r.status_code == 403


def test_authorize_garbage_state_rejected(client, user_a, github_stub, monkeypatch):
    _configure_stub_env(monkeypatch, github_stub)
    r = client.post(
        "/api/github/authorize/callback", json={"code": "c", "state": "nonsense!12"}, headers=user_a["headers"]
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Highlights (the "view their GitHub highlights" surface)


def test_highlights_after_link(client, user_a, github_stub, monkeypatch):
    _configure_stub_env(monkeypatch, github_stub)
    github_stub.scenario = "ok"

    # link first
    start = client.post("/api/github/device/start", headers=user_a["headers"]).json()
    client.post("/api/github/device/poll", json={"device_code": start["device_code"]}, headers=user_a["headers"])

    r = client.get("/api/github/highlights", headers=user_a["headers"])
    assert r.status_code == 200, r.text
    h = r.json()
    assert h["login"] == "octocat"
    assert h["profile"]["public_repos"] == 8
    assert h["profile"]["followers"] == 4200
    assert h["repos"][0]["name"] == "Spoon-Knife"
    assert h["repos"][0]["stars"] == 12345
    assert h["events"][0]["detail"] == "pushed 2 commit(s) to octocat/Spoon-Knife"
    assert h["events"][1]["detail"] == "starred cli/cli"
    assert h["cached"] is False

    # second call serves the cache (cached=true) — the rate-limit QoL
    r = client.get("/api/github/highlights", headers=user_a["headers"])
    assert r.status_code == 200
    assert r.json()["cached"] is True

    # refresh=true busts it
    r = client.get("/api/github/highlights?refresh=true", headers=user_a["headers"])
    assert r.status_code == 200
    assert r.json()["cached"] is False


def test_highlights_409_when_unlinked(client, user_a, github_stub, monkeypatch):
    _configure_stub_env(monkeypatch, github_stub)
    r = client.get("/api/github/highlights", headers=user_a["headers"])
    assert r.status_code == 409
    assert "No GitHub account linked" in r.json()["detail"]


def test_unlink_after_link(client, user_a, github_stub, monkeypatch):
    _configure_stub_env(monkeypatch, github_stub)
    github_stub.scenario = "ok"

    start = client.post("/api/github/device/start", headers=user_a["headers"]).json()
    client.post("/api/github/device/poll", json={"device_code": start["device_code"]}, headers=user_a["headers"])

    r = client.delete("/api/github/link", headers=user_a["headers"])
    assert r.status_code == 204

    r = client.get("/api/github/status", headers=user_a["headers"])
    assert r.json()["linked"] is False

    # highlights now 409 again; double-unlink 404s
    assert client.get("/api/github/highlights", headers=user_a["headers"]).status_code == 409
    assert client.delete("/api/github/link", headers=user_a["headers"]).status_code == 404


def test_link_visibility_is_isolated(client, user_a, user_b, github_stub, monkeypatch):
    _configure_stub_env(monkeypatch, github_stub)
    github_stub.scenario = "ok"

    start = client.post("/api/github/device/start", headers=user_a["headers"]).json()
    client.post("/api/github/device/poll", json={"device_code": start["device_code"]}, headers=user_a["headers"])

    # user B sees no link, no highlights, and cannot unlink A's
    assert client.get("/api/github/status", headers=user_b["headers"]).json()["linked"] is False
    assert client.get("/api/github/highlights", headers=user_b["headers"]).status_code == 409
    assert client.delete("/api/github/link", headers=user_b["headers"]).status_code == 404
