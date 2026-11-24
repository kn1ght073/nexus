"""Interactive Google OAuth and Session Token Authentication Modal for NEXUS TUI."""

import http.server
import socket
import threading
import time
from typing import Optional
import urllib.parse
import webbrowser

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from ...client import get_client
from ...config import CredentialStore, load_config, save_config, validate_session
from ...errors import NexusError


class _TUIOAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    result_holder: dict = {}

    def log_message(self, format, *args):
        pass  # Suppress default server access logs

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        token = query.get("token", [None])[0]
        refresh = query.get("refresh", [None])[0]
        if token:
            self.result_holder["token"] = token
            if refresh:
                self.result_holder["refresh"] = refresh
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","message":"CLI authorized via Google OAuth"}')
        else:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"error","message":"Missing session token"}')


class LoginModal(ModalScreen[bool]):
    """Modal dialog for authenticating operator via Google OAuth or direct session token."""

    def __init__(self) -> None:
        super().__init__()
        self._oauth_server: Optional[http.server.HTTPServer] = None
        self._stop_oauth = threading.Event()

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box", id="login-modal-box"):
            yield Label("🔑 NEXUS OPERATOR AUTHENTICATION", classes="modal-header")
            yield Static(
                "NEXUS requires authentication via Google OAuth to link your sovereign identity,\n"
                "enable encrypted sync, and access remote nodes.\n",
                id="login-intro-static",
            )

            # Option 1: Browser OAuth
            yield Label("Option 1: Sign in with Google in Browser", classes="modal-section-title")
            with Horizontal(classes="modal-row"):
                yield Button("🌐 Open Browser for Google OAuth", id="btn-oauth-browser", variant="primary")

            yield Static("", id="login-oauth-status")

            # Option 2: Paste Token
            yield Label("\nOption 2: Direct Session Token (JWT)", classes="modal-section-title")
            yield Input(
                placeholder="Paste JWT session token here...",
                id="input-login-token",
                password=True,
            )

            yield Static("", id="login-status-msg")

            with Horizontal(classes="modal-footer"):
                yield Button("Validate & Sign In", variant="success", id="btn-submit-token", classes="modal-button")
                yield Button("Cancel", variant="default", id="btn-cancel-login", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-login":
            self._cleanup_server()
            self.dismiss(False)
            return

        if event.button.id == "btn-oauth-browser":
            self._start_browser_oauth()
            return

        if event.button.id == "btn-submit-token":
            token_val = self.query_one("#input-login-token", Input).value.strip()
            if not token_val:
                status = self.query_one("#login-status-msg", Static)
                status.update("[red]Error: Please enter a session token.[/red]")
                return
            self._verify_and_store_token(token_val)

    def _start_browser_oauth(self) -> None:
        status = self.query_one("#login-oauth-status", Static)
        status.update("[cyan]● Starting local callback listener and opening browser...[/cyan]")

        def find_free_port() -> int:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))
                return s.getsockname()[1]

        try:
            port = find_free_port()
            _TUIOAuthCallbackHandler.result_holder = {}
            server = http.server.HTTPServer(("127.0.0.1", port), _TUIOAuthCallbackHandler)
            server.timeout = 1.0
            self._oauth_server = server
            self._stop_oauth.clear()

            cfg = load_config()
            target_url = cfg.api_url.rstrip("/")
            auth_url = f"{target_url}/api/auth/google/start?cli_port={port}"

            try:
                webbrowser.open(auth_url)
            except Exception:
                pass

            status.update(
                f"[bold cyan]Waiting for browser authentication on port {port}...[/bold cyan]\n"
                f"[dim]URL: {auth_url}[/dim]"
            )

            def poll_worker():
                start = time.time()
                while time.time() - start < 90 and not self._stop_oauth.is_set():
                    server.handle_request()
                    if "token" in _TUIOAuthCallbackHandler.result_holder:
                        tok = _TUIOAuthCallbackHandler.result_holder["token"]
                        ref = _TUIOAuthCallbackHandler.result_holder.get("refresh")
                        self.app.call_from_thread(self._on_oauth_success, tok, ref)
                        return

                if not self._stop_oauth.is_set():
                    self.app.call_from_thread(
                        self._on_oauth_timeout,
                        "Timeout waiting for browser callback. You can paste token directly below.",
                    )

            t = threading.Thread(target=poll_worker, daemon=True)
            t.start()

        except Exception as e:
            status.update(f"[red]Could not start local listener: {e}[/red]")

    def _on_oauth_success(self, token: str, refresh: Optional[str] = None) -> None:
        self._cleanup_server()
        self._verify_and_store_token(token, refresh=refresh)

    def _on_oauth_timeout(self, message: str) -> None:
        self._cleanup_server()
        try:
            status = self.query_one("#login-oauth-status", Static)
            status.update(f"[yellow]{message}[/yellow]")
        except Exception:
            pass

    def _verify_and_store_token(self, token: str, refresh: Optional[str] = None) -> None:
        status = self.query_one("#login-status-msg", Static)
        status.update("[cyan]Verifying session with control plane...[/cyan]")

        def verify_worker():
            cfg = load_config()
            client = get_client()
            try:
                resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=4)
                if resp.status_code == 200:
                    data = resp.json()
                    email = data.get("email", "operator")
                    cfg.token = token
                    if refresh:
                        cfg.refresh_token = refresh
                    cfg.email = email
                    save_config(cfg)
                    self.app.call_from_thread(self._finish_success, email)
                else:
                    self.app.call_from_thread(self._finish_error, f"Session verification failed (HTTP {resp.status_code})")
            except Exception as e:
                self.app.call_from_thread(self._finish_error, f"Verification failed: {e}")

        t = threading.Thread(target=verify_worker, daemon=True)
        t.start()

    def _finish_success(self, email: str) -> None:
        self._cleanup_server()
        self.dismiss(True)

    def _finish_error(self, err: str) -> None:
        try:
            status = self.query_one("#login-status-msg", Static)
            status.update(f"[red]{err}[/red]")
        except Exception:
            pass

    def _cleanup_server(self) -> None:
        self._stop_oauth.set()
        if self._oauth_server:
            try:
                self._oauth_server.server_close()
            except Exception:
                pass
            self._oauth_server = None
