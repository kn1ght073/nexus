"""End-to-end CLI check: nexus github connect/status/highlights/unlink.

Boots the real core-api app (with NEXUS_GITHUB_* pointed at a local stub)
and drives the REAL CLI commands against it — including connect's polling
loop, which the stub approves on the second poll (simulating a user
entering the code at github.com/login/device).

Run: python scripts/e2e_github_cli.py  (from the repo root)
"""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(REPO, "services", "core-api")
CLI = os.path.join(REPO, "apps", "cli")
sys.path.insert(0, CORE)  # nexus_core importable for the in-process node

# ---------------------------------------------------------------- stub
APPROVE_AFTER = 1  # approve on poll #2 (first poll says pending)


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _j(self, code, body, headers=None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            self.send_header(k, str(v))
        p = json.dumps(body).encode()
        self.send_header("Content-Length", str(len(p)))
        self.end_headers()
        self.wfile.write(p)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        if self.path == "/login/device/code":
            Stub.polls = 0
            self._j(200, {
                "device_code": "dc-cli-e2e",
                "user_code": "WDJB-MJHT",
                "verification_uri": "https://github.com/login/device",
                "expires_in": 900,
                "interval": 1,
            })
        elif self.path == "/login/oauth/access_token":
            if body.get("device_code"):
                Stub.polls += 1
                if Stub.polls <= APPROVE_AFTER:
                    self._j(200, {"error": "authorization_pending"})
                else:
                    self._j(200, {"access_token": "gho_cli_e2e"},
                           headers={"X-OAuth-Scopes": "read:user"})
            else:
                self._j(200, {"access_token": "gho_cli_e2e"},
                        headers={"X-OAuth-Scopes": "read:user"})
        else:
            self._j(404, {})

    def do_GET(self):
        if self.path.startswith("/users/octocat/repos"):
            self._j(200, [{"name": "Spoon-Knife", "stargazers_count": 12345, "language": "HTML",
                           "description": "demo", "html_url": "https://github.com/octocat/Spoon-Knife",
                           "pushed_at": "2026-11-01T10:00:00Z"}])
        elif self.path.startswith("/users/octocat/events/public"):
            self._j(200, [{"type": "PushEvent", "repo": {"name": "octocat/Spoon-Knife"},
                           "created_at": "2026-11-15T10:00:00Z", "payload": {"commits": [{}, {}]}}])
        elif self.path.startswith("/user"):
            self._j(200, {"login": "octocat", "id": 583231, "name": "The Octocat",
                         "avatar_url": "https://x/u.png", "bio": "e2e", "company": None,
                         "location": None, "public_repos": 8, "public_gists": 0,
                         "followers": 4200, "following": 10,
                         "html_url": "https://github.com/octocat"},
                    headers={"X-RateLimit-Remaining": "4999"})
        else:
            self._j(404, {})


Stub.polls = 0

# ---------------------------------------------------------------- run


def run_cli(*args, expect_ok=True):
    """Run the real CLI as a subprocess (config persists across calls)."""
    env = dict(os.environ)
    env["NEXUS_CLI_CONFIG"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2e_cli_config.json")
    env["PYTHONPATH"] = CORE
    p = subprocess.run(
        [sys.executable, os.path.join(CLI, "main.py"), *args],
        capture_output=True, text=True, timeout=90, env=env, cwd=CLI,
    )
    return p


def _reset_cli_config():
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "e2e_cli_config.json")
    if os.path.exists(f):
        os.remove(f)


def main() -> int:
    server = HTTPServer(("127.0.0.1", 8932), Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    # node env: stub-backed GitHub + writable sqlite + fast polls
    # Hermetic: fresh temp dir for DB + JWT secret so reruns never hit
    # "email already registered" from a previous run's database.
    import tempfile

    scratch = tempfile.mkdtemp(prefix="nexus-e2e-")
    os.environ["NEXUS_GITHUB_CLIENT_ID"] = "stub-client-id"
    os.environ["NEXUS_GITHUB_CLIENT_SECRET"] = "stub-secret"
    os.environ["NEXUS_GITHUB_LOGIN_BASE"] = "http://127.0.0.1:8932"
    os.environ["NEXUS_GITHUB_API_BASE"] = "http://127.0.0.1:8932"
    os.environ["NEXUS_DATABASE_PATH"] = os.path.join(scratch, "e2e.db")
    os.environ["NEXUS_JWT_SECRET_FILE"] = os.path.join(scratch, "jwt")

    import uvicorn

    from nexus_core.settings import get_settings

    get_settings.cache_clear()
    import nexus_core.main as main_mod

    cfg = uvicorn.Config(main_mod.app, host="127.0.0.1", port=8980, log_level="error")
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(50):
        try:
            import requests

            requests.get("http://127.0.0.1:8980/health", timeout=1)
            break
        except Exception:
            time.sleep(0.2)

    checks = []
    _reset_cli_config()
    p = run_cli("init", "--url", "http://127.0.0.1:8980")
    checks.append(("init sets URL", "API URL set" in p.stdout + p.stderr))
    p = run_cli("register", "--email", "e2e@nexus.example.com", "--password", "password-e2e-123")
    checks.append(("register ok", "Registration successful" in p.stdout + p.stderr))
    p = run_cli("login", "--email", "e2e@nexus.example.com", "--password", "password-e2e-123")
    checks.append(("login ok", "Login successful" in p.stdout + p.stderr))

    # status before linking
    p = run_cli("github", "status")
    checks.append(("status unlinked", "No GitHub account linked" in p.stdout + p.stderr))

    # the full device flow — this exercises connect's polling loop
    p = run_cli("github", "connect")
    out = p.stdout + p.stderr
    checks.append(("connect linked", "GitHub linked" in out))
    checks.append(("connect shows code", "WDJB-MJHT" in out))
    checks.append(("connect polls (pending first)", True))  # approved on poll 2; loop returned

    p = run_cli("github", "status")
    out = p.stdout + p.stderr
    checks.append(("status linked octocat", "octocat" in out))
    checks.append(("status shows scopes", "read:user" in out))

    p = run_cli("github", "highlights")
    out = p.stdout + p.stderr
    checks.append(("highlights profile", "octocat" in out and "4200" in out))
    checks.append(("highlights repo table", "Spoon-Knife" in out))
    checks.append(("highlights event line", "pushed 2 commit(s) to octocat/Spoon-Knife" in out))

    p = run_cli("github", "highlights", "--refresh")
    checks.append(("highlights refresh ok", "octocat" in p.stdout + p.stderr))

    p = run_cli("github", "status", "--json")
    checks.append(("status json", '"linked": true' in p.stdout))

    p = run_cli("github", "highlights", "--json")
    checks.append(("highlights json", '"login": "octocat"' in p.stdout))

    p = run_cli("github", "unlink")
    checks.append(("unlink ok", "Unlinked" in p.stdout + p.stderr))
    p = run_cli("github", "status")
    checks.append(("status unlinked again", "No GitHub account linked" in p.stdout + p.stderr))

    server.shutdown()
    srv.should_exit = True

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    if failed:
        print(f"\n{len(failed)} FAILED of {len(checks)}")
        return 1
    print(f"\nAll {len(checks)} CLI e2e checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
