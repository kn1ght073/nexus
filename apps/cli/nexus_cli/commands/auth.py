"""Authentication and identity commands."""

from typing import Optional

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


@auth_app.command("login")
def login(
    email: str = typer.Option(..., prompt=True, help="Account email address"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Account password"),
    url: Optional[str] = typer.Option(None, "--url", help="API URL (defaults to configured api_url)"),
):
    """Log in to NEXUS Core and securely store credentials."""
    cfg = load_config()
    target_url = url if isinstance(url, str) and url else cfg.api_url
    client = get_client(base_url=target_url)

    try:
        with status_spinner(f"Authenticating with {target_url}…"):
            resp = client.post("/api/auth/login", json={"email": email, "password": password})
        tokens = resp.json()

        cfg.token = tokens["access_token"]
        if tokens.get("refresh_token"):
            cfg.refresh_token = tokens["refresh_token"]
        cfg.email = email
        if url and isinstance(url, str):
            cfg.api_url = url.rstrip("/")
        save_config(cfg)

        console.print(
            Panel(
                f"Logged in as [bold cyan]{email}[/bold cyan].",
                title="[bold green]Login successful[/bold green]",
                border_style="green",
                expand=False,
            )
        )
    except NexusError as e:
        console.print(
            Panel(
                f"Could not reach NEXUS at {target_url}.\n[dim]{e.message}[/dim]",
                title="[bold red]Login failed[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        raise typer.Exit(ExitCode.AUTH_ERROR)


@auth_app.command("register")
def register(
    email: str = typer.Option(..., prompt=True, help="New account email"),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True, help="Password (8+ chars)"),
    url: Optional[str] = typer.Option(None, "--url", help="API URL"),
):
    """Register a new NEXUS user account."""
    if len(password) < 8:
        console.print(
            Panel("Password must be at least 8 characters.", title="[bold red]Registration failed[/bold red]", border_style="red", expand=False)
        )
        raise typer.Exit(ExitCode.USAGE_ERROR)

    target_url = url if isinstance(url, str) and url else None
    client = get_client(base_url=target_url)
    try:
        with status_spinner("Creating account…"):
            resp = client.post("/api/auth/register", json={"email": email, "password": password})
        console.print(
            Panel(
                "Account created. Now run [bold cyan]nexus login[/bold cyan].",
                title="[bold green]Registration successful[/bold green]",
                border_style="green",
                expand=False,
            )
        )
    except NexusError as e:
        console.print(
            Panel(f"{e.message}", title="[bold red]Registration failed[/bold red]", border_style="red", expand=False)
        )
        raise typer.Exit(e.exit_code)


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
