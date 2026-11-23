"""Authentication and identity commands."""

import http.server
import socket
import threading
import time
from typing import Optional
import urllib.parse
import webbrowser

import typer
from rich.panel import Panel

from ..client import get_client
from ..config import CredentialStore, load_config, save_config
from ..errors import AuthenticationError, ExitCode, NexusError
from ..ui import (
    console,
    is_json_mode,
    output_json,
    print_error,
    print_info,
    print_success,
    render_key_value,
    set_json_mode,
    status_spinner,
)

auth_app = typer.Typer(help="Manage authentication and user identity")


class _OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    result_holder: dict[str, str] = {}

    def log_message(self, format, *args):
        pass  # Suppress default server access logs on stdout/stderr

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
            self.wfile.write(b'{"status":"ok","message":"CLI authorized"}')
        else:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"error","message":"Missing token"}')


@auth_app.command("login")
def login(
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Direct session token from Control Center"),
    email: Optional[str] = typer.Option(None, "--email", help="(Disabled) Legacy email"),
    password: Optional[str] = typer.Option(None, "--password", help="(Disabled) Legacy password"),
    url: Optional[str] = typer.Option(None, "--url", help="API URL (defaults to configured api_url)"),
):
    """Log in to NEXUS Core via Google OAuth and securely store credentials."""
    cfg = load_config()
    target_url = url if isinstance(url, str) and url else cfg.api_url
    client = get_client(base_url=target_url)

    if email and password and not token:
        console.print(
            Panel(
                "Password authentication is disabled.\nNEXUS accounts authenticate exclusively via Google OAuth.",
                title="[bold yellow]Notice[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )

    access_token = token
    refresh_token = None

    if not access_token:
        def find_free_port() -> int:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))
                return s.getsockname()[1]

        port = find_free_port()
        _OAuthCallbackHandler.result_holder = {}
        server = http.server.HTTPServer(("127.0.0.1", port), _OAuthCallbackHandler)
        server.timeout = 1.5

        auth_url = f"{target_url.rstrip('/')}/api/auth/google/start?cli_port={port}"
        console.print(
            Panel(
                f"Opening browser for Google OAuth sign-in:\n[bold cyan]{auth_url}[/bold cyan]\n\n"
                "[dim]After authenticating, your CLI will capture the session automatically.\n"
                "If the browser does not open, visit the URL above or copy your session token from the web console.[/dim]",
                title="[bold cyan]Google OAuth Authentication[/bold cyan]",
                border_style="cyan",
                expand=False,
            )
        )

        try:
            webbrowser.open(auth_url)
        except Exception:
            pass

        with status_spinner("Waiting for Google OAuth authentication in browser…"):
            start_time = time.time()
            while time.time() - start_time < 90:
                server.handle_request()
                if "token" in _OAuthCallbackHandler.result_holder:
                    access_token = _OAuthCallbackHandler.result_holder["token"]
                    refresh_token = _OAuthCallbackHandler.result_holder.get("refresh")
                    break

        server.server_close()

        if not access_token:
            console.print("[yellow]Automatic callback did not complete within timeout.[/yellow]")
            access_token = typer.prompt("Paste Session Token from Control Center (or press Ctrl+C to cancel)")
            if not access_token:
                print_error("No session token provided. Login aborted.")
                raise typer.Exit(ExitCode.AUTH_ERROR)

    # Validate token against the target control plane
    try:
        with status_spinner(f"Verifying session with {target_url}…"):
            resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
            data = resp.json()
            user_email = data.get("email", "unknown")
            user_role = data.get("role", "user")

        cfg.token = access_token
        if refresh_token:
            cfg.refresh_token = refresh_token
        cfg.email = user_email
        if url and isinstance(url, str):
            cfg.api_url = url.rstrip("/")
        save_config(cfg)

        console.print(
            Panel(
                f"Logged in as [bold cyan]{user_email}[/bold cyan] ([bold]{user_role}[/bold]) via Google OAuth.\n"
                f"Session token stored securely in [bold]{CredentialStore.get_backend_name()}[/bold].",
                title="[bold green]Login successful[/bold green]",
                border_style="green",
                expand=False,
            )
        )
    except NexusError as e:
        console.print(
            Panel(
                f"Could not reach or verify session with NEXUS at {target_url}.\n[dim]{e.message}[/dim]",
                title="[bold red]Login failed[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        raise typer.Exit(ExitCode.AUTH_ERROR)


@auth_app.command("register")
def register(
    email: Optional[str] = typer.Option(None, "--email", help="(Disabled) Legacy email"),
    password: Optional[str] = typer.Option(None, "--password", help="(Disabled) Legacy password"),
    url: Optional[str] = typer.Option(None, "--url", help="API URL"),
):
    """Register a new NEXUS user account via Google OAuth."""
    console.print(
        Panel(
            "Account registration is exclusively handled via Google OAuth.\n"
            "Authenticating with your Google account will automatically provision\n"
            "and register your operator identity in the NEXUS database.",
            title="[bold cyan]Google OAuth Registration Policy[/bold cyan]",
            border_style="cyan",
            expand=False,
        )
    )
    login(token=None, email=None, password=None, url=url)


@auth_app.command("logout")
def logout():
    """Revoke active session and purge stored credentials."""
    cfg = load_config()
    client = get_client()

    if cfg.token:
        try:
            client.post("/api/auth/logout", json={"refresh_token": cfg.refresh_token})
        except Exception:
            pass
        if cfg.control_plane_url and cfg.control_plane_url != cfg.api_url:
            try:
                cp_client = get_client(base_url=cfg.control_plane_url)
                cp_client.post("/api/auth/logout", json={"refresh_token": cfg.refresh_token})
            except Exception:
                pass

    cfg.token = None
    cfg.refresh_token = None
    cfg.email = None
    cfg.node_id = None
    cfg.node_api_key = None
    save_config(cfg)

    console.print(
        Panel("Logged out — stored credentials cleared.", title="[bold green]SUCCESS[/bold green]", border_style="green", expand=False)
    )


@auth_app.command("whoami")
def whoami(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Display identity and privileges of the current session."""
    if json_output:
        set_json_mode(True)
    cfg = load_config()
    client = get_client()

    if not cfg.token:
        print_info("Not authenticated. Run 'nexus auth login'.", title="WHOAMI")
        return

    try:
        with status_spinner("Inspecting identity…"):
            resp = client.get("/api/auth/me")
        data = resp.json()
        if is_json_mode():
            output_json(data)
            return

        render_key_value(
            {
                "User ID": str(data.get("id")),
                "Email": data.get("email"),
                "Role": data.get("role", "user"),
                "Created At": data.get("created_at", "")[:19],
                "API Endpoint": cfg.api_url,
            },
            title="AUTHENTICATED IDENTITY",
        )
    except NexusError as e:
        print_error(e.message, title="WHOAMI FAILED")
        raise typer.Exit(e.exit_code)


@auth_app.command("status")
def auth_status(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Check connectivity and active session state."""
    if json_output:
        set_json_mode(True)
    cfg = load_config()

    status_data = {
        "authenticated": bool(cfg.token),
        "email": cfg.email,
        "api_url": cfg.api_url,
        "control_plane_url": cfg.control_plane_url,
        "node_id": cfg.node_id,
        "keyring_enabled": CredentialStore.is_keyring_enabled(),
    }

    if is_json_mode():
        output_json(status_data)
        return

    auth_line = f"[bold green]Authenticated[/bold green] as [bold]{cfg.email}[/bold]" if cfg.token else "[yellow]Unauthenticated[/yellow]"
    render_key_value(
        {
            "Status": auth_line,
            "Target API": cfg.api_url,
            "Control Plane": cfg.control_plane_url or "None",
            "Hardware Node": f"#{cfg.node_id}" if cfg.node_id else "Unclaimed",
            "Keyring Security": "Active (OS Keyring)" if status_data["keyring_enabled"] else "Fallback (File mode 0600)",
        },
        title="AUTH STATUS",
    )
