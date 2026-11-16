#!/usr/bin/env python3
"""NEXUS demo setup — the full first-run journey, end to end.

Runs on Windows / macOS / Linux with only Python 3.11+ (no pip installs
needed beforehand). The demo walks the exact user journey:

  1. environment bootstrap   (nexus bootstrap --yes → managed venv, uv or pip)
  2. node boots FROM the venv (uvicorn nexus_core.main:app)
  3. register + login        (real auth: Argon2 + JWT)
  4. GitHub linking          (device flow + authorize flow against a local
                              GitHub STUB — no real GitHub app needed, no
                              network beyond loopback)
  5. GitHub highlights       (profile/repos/events through the node cache)
  6. interactive interview   (scripted answers replay: mirror choice etc.)
  7. unlink + teardown

Every step prints PASS/FAIL. Any failure prints the exact error so it can
be fixed feature-by-feature — that is how this script is meant to be used:
run it after each change; fix what's red; run again.

Usage:
  python demo_setup.py                 # full demo (venv in ./demo-venv)
  python demo_setup.py --keep          # keep venv + db for inspection
  python demo_setup.py --skip-bootstrap# reuse an existing demo-venv
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "services" / "core-api"
CLI = REPO / "apps" / "cli"
DEM = Path(__file__).resolve().parent

NODE_PORT = 8987
STUB_PORT = 8988
VENV_DIR = DEM / "demo-venv"

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, note: str = "") -> None:
    RESULTS.append((name, ok, note))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{note}]" if note and not ok else ""))


# ---------------------------------------------------------------------------
# The GitHub STUB (loopback only): device flow + token + profile/repos/events
# ---------------------------------------------------------------------------
def start_github_stub() -> tuple[threading.Thread, object]:
    from http.server import BaseHTTPRequestHandler, HTTPServer

    approved = {"n": 0}  # poll counter — approve on the 2nd poll like a user typing the code

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
                approved["n"] = 0
                self._j(200, {
                    "device_code": "dc-demo",
                    "user_code": "DEMO-1234",
                    "verification_uri": "https://github.com/login/device",
                    "expires_in": 900,
                    "interval": 1,
                })
            elif self.path == "/login/oauth/access_token":
                if body.get("device_code"):
                    approved["n"] += 1
                    if approved["n"] < 2:
                        self._j(200, {"error": "authorization_pending"})
                    else:
                        self._j(200, {"access_token": "gho_demo"},
                                headers={"X-OAuth-Scopes": "read:user"})
                else:
                    self._j(200, {"access_token": "gho_demo"},
                            headers={"X-OAuth-Scopes": "read:user"})
            else:
                self._j(404, {})

        def do_GET(self):
            if self.path.startswith("/users/octocat/repos"):
                self._j(200, [{"name": "Spoon-Knife", "stargazers_count": 12345,
                               "language": "HTML", "description": "demo",
                               "html_url": "https://github.com/octocat/Spoon-Knife",
                               "pushed_at": "2026-11-01T10:00:00Z"}])
            elif self.path.startswith("/users/octocat/events/public"):
                self._j(200, [{"type": "PushEvent", "repo": {"name": "octocat/Spoon-Knife"},
                               "created_at": "2026-11-15T10:00:00Z",
                               "payload": {"commits": [{}, {}]}},
                              {"type": "WatchEvent", "repo": {"name": "cli/cli"},
                               "created_at": "2026-11-14T10:00:00Z", "payload": {}}])
            elif self.path.startswith("/user"):
                self._j(200, {"login": "octocat", "id": 583231, "name": "The Octocat",
                              "avatar_url": "https://x/u.png", "bio": "demo",
                              "company": None, "location": None, "public_repos": 8,
                              "public_gists": 0, "followers": 4200, "following": 10,
                              "html_url": "https://github.com/octocat"},
                        headers={"X-RateLimit-Remaining": "4999"})
            else:
                self._j(404, {})

    server = HTTPServer(("127.0.0.1", STUB_PORT), Stub)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return t, server


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def venv_python() -> Path:
    inner = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return VENV_DIR / inner / f"python{suffix}"


def wait_http(url: str, seconds: float = 20.0) -> bool:
    import urllib.request

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def api(method: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    import urllib.request

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{NODE_PORT}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"detail": str(e)}


def run_cli(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["NEXUS_CLI_CONFIG"] = str(DEM / "demo_cli_config.json")
    env["PYTHONPATH"] = str(CORE)
    return subprocess.run(
        [sys.executable, str(CLI / "main.py"), *args],
        capture_output=True, text=True, timeout=300, env=env, cwd=str(CLI),
        input=stdin,
    )


# ---------------------------------------------------------------------------
# demo steps
# ---------------------------------------------------------------------------
def step_bootstrap(skip: bool) -> None:
    if skip:
        check("bootstrap (skipped, reusing venv)", venv_python().exists(), "venv missing")
        return
    if VENV_DIR.exists():
        import shutil

        shutil.rmtree(VENV_DIR)
    p = run_cli("bootstrap", "--yes", "--venv-dir", str(VENV_DIR))
    out = p.stdout + p.stderr
    check("bootstrap runs inside the app", "Setup complete" in out, out[-400:])
    check("managed venv exists", venv_python().exists())
    probe = subprocess.run([str(venv_python()), "-c", "import nexus_core; print(nexus_core.__file__)"],
                           capture_output=True, text=True, timeout=60)
    check("venv imports nexus_core (editable)", probe.returncode == 0, probe.stderr[-300:])


def start_node() -> subprocess.Popen | None:
    env = dict(os.environ)
    env["NEXUS_DATABASE_PATH"] = str(DEM / "demo.db")
    env["NEXUS_JWT_SECRET_FILE"] = str(DEM / "demo_jwt")
    env["NEXUS_GITHUB_CLIENT_ID"] = "demo-client-id"
    env["NEXUS_GITHUB_CLIENT_SECRET"] = "demo-secret"
    env["NEXUS_GITHUB_LOGIN_BASE"] = f"http://127.0.0.1:{STUB_PORT}"
    env["NEXUS_GITHUB_API_BASE"] = f"http://127.0.0.1:{STUB_PORT}"
    log = open(DEM / "demo_node.log", "w")
    proc = subprocess.Popen(
        [str(venv_python()), "-m", "uvicorn", "nexus_core.main:app",
         "--host", "127.0.0.1", "--port", str(NODE_PORT), "--log-level", "error"],
        env=env, stdout=log, stderr=subprocess.STDOUT, cwd=str(CORE),
    )
    ok = wait_http(f"http://127.0.0.1:{NODE_PORT}/health")
    code, body = api("GET", "/health")
    check("node boots from the managed venv", ok and body.get("status") == "ok", open(DEM / "demo_node.log").read()[-500:] if not ok else "")
    return proc


def step_auth() -> str | None:
    code, _ = api("POST", "/api/auth/register",
                  body={"email": "demo@nexus.example.com", "password": "password-demo-123"})
    check("register (real Argon2+JWT auth)", code == 201, f"HTTP {code}")
    code, body = api("POST", "/api/auth/login",
                     body={"email": "demo@nexus.example.com", "password": "password-demo-123"})
    check("login", code == 200 and "access_token" in body, f"HTTP {code}")
    return body.get("access_token")


def step_github_link(token: str) -> None:
    code, start = api("POST", "/api/github/device/start", token, {})
    check("github device flow starts (user code issued)", code == 200 and start.get("user_code") == "DEMO-1234", f"HTTP {code}")

    # poll twice: pending → linked (the stub approves on poll 2)
    code, poll1 = api("POST", "/api/github/device/poll", token, {"device_code": start["device_code"]})
    check("poll #1 reports pending (user hasn't typed code)", poll1.get("status") == "pending", json.dumps(poll1))
    code, poll2 = api("POST", "/api/github/device/poll", token, {"device_code": start["device_code"]})
    check("poll #2 links the account", poll2.get("status") == "linked" and poll2["profile"]["login"] == "octocat", json.dumps(poll2))

    code, status = api("GET", "/api/github/status", token)
    check("status shows the link (token never exposed)", status.get("linked") is True and "gho_demo" not in json.dumps(status), json.dumps(status))

    # authorize-code flow (the desktop path)
    code, url = api("GET", "/api/github/authorize-url", token)
    check("authorize-url issued (desktop flow)", code == 200 and "/login/oauth/authorize" in url["url"], json.dumps(url))
    code, cb = api("POST", "/api/github/authorize/callback", token, {"code": "demo-code", "state": url["state"]})
    check("authorize callback re-links (single-use state)", code == 200 and cb.get("status") == "linked", json.dumps(cb))


def step_highlights(token: str) -> None:
    code, h = api("GET", "/api/github/highlights", token)
    ok = code == 200 and h.get("login") == "octocat" and h["profile"]["followers"] == 4200
    check("highlights: profile served", ok, f"HTTP {code} {json.dumps(h)[:200]}")
    check("highlights: repos slimmed", h.get("repos", [{}])[0].get("stars") == 12345, json.dumps(h.get("repos")))
    details = [e.get("detail", "") for e in h.get("events", [])]
    check("highlights: events summarized", any("pushed 2 commit(s)" in d for d in details), json.dumps(details))
    code, h2 = api("GET", "/api/github/highlights", token)
    check("highlights: second call hits cache", h2.get("cached") is True, json.dumps({k: h2.get(k) for k in ("cached",)}))
    code, h3 = api("GET", "/api/github/highlights?refresh=true", token)
    check("highlights: refresh busts cache", code == 200 and h3.get("cached") is False, json.dumps({k: h3.get(k) for k in ("cached",)}))


def step_interview() -> None:
    # scripted answers: yes install → yes slow link → tuna → run plan (dry-run so nothing installs)
    p = run_cli("bootstrap", "--dry-run", stdin="y\ny\ntuna\ny\n")
    out = p.stdout + p.stderr
    check("interactive interview asks what to install", "Install the full NEXUS stack" in out, out[-300:])
    check("mirror guidance offered on slow link", "Known mirrors" in out, out[-300:])
    check("chosen mirror propagates into plan", "pypi.tuna.tsinghua.edu.cn" in out, out[-300:])
    p = run_cli("bootstrap", "--dry-run", stdin="n\n")
    out = p.stdout + p.stderr
    check("decline path gives guidance, exits clean", "Setup deferred" in out and p.returncode == 0, out[-300:])


def step_unlink(token: str) -> None:
    code, _ = api("DELETE", "/api/github/link", token)
    check("unlink (token revoked server-side)", code == 204, f"HTTP {code}")
    code, status = api("GET", "/api/github/status", token)
    check("status unlinked after", status.get("linked") is False, json.dumps(status))
    code, _ = api("GET", "/api/github/highlights", token)
    check("highlights 409 after unlink", code == 409, f"HTTP {code}")


def main() -> int:
    parser = argparse.ArgumentParser(description="NEXUS end-to-end demo setup")
    parser.add_argument("--keep", action="store_true", help="keep venv + artifacts")
    parser.add_argument("--skip-bootstrap", action="store_true", help="reuse existing demo-venv")
    args = parser.parse_args()

    print(f"NEXUS demo — repo: {REPO}\n")
    sys.path.insert(0, str(CORE))

    stub_thread, stub = start_github_stub()
    step_bootstrap(args.skip_bootstrap)
    node = start_node()
    try:
        if node is None:
            print("\nnode failed to start — aborting remaining steps")
            return 1
        token = step_auth()
        if token:
            step_github_link(token)
            step_highlights(token)
            step_interview()
            step_unlink(token)
    finally:
        if node:
            node.terminate()
            try:
                node.wait(timeout=10)
            except Exception:
                node.kill()
        stub.shutdown()

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{'=' * 60}\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("FAILURES:")
        for name, _, note in failed:
            print(f"  - {name}: {note[:300]}")
    if not args.keep:
        for f in (DEM / "demo.db", DEM / "demo_jwt", DEM / "demo_cli_config.json",
                  DEM / "demo_node.log"):
            f.unlink(missing_ok=True)
        if not args.skip_bootstrap:
            import shutil

            shutil.rmtree(VENV_DIR, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
