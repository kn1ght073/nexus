"""Main Typer CLI Application — Command registration, routing, and backward compatibility."""

import os
from typing import Optional

import typer
from rich.panel import Panel

from nexus_cli import __version__
from nexus_cli.client import get_client
from nexus_cli.commands.account import account_app
from nexus_cli.commands.auth import auth_app
from nexus_cli.commands.config_cmd import config_app
from nexus_cli.commands.devices import devices_app
from nexus_cli.commands.doctor import doctor_cmd
from nexus_cli.commands.files import files_app
from nexus_cli.commands.github import github_app
from nexus_cli.commands.nodes import nodes_app
from nexus_cli.commands.notes import notes_app
from nexus_cli.commands.projects import projects_app
from nexus_cli.commands.services import services_app
from nexus_cli.commands.sync import sync_app
from nexus_cli.commands.tasks import tasks_app
from nexus_cli.config import load_config, save_config
from nexus_cli.errors import ExitCode, NexusError
from nexus_cli.ui import console, output_json, print_error, print_success, set_json_mode, status_spinner

app = typer.Typer(
    name="nexus",
    help="NEXUS CLI — Modern Developer Interface & Edge Node Controller",
    no_args_is_help=True,
    add_completion=False,
)

# Attach modern subcommand groupings
app.add_typer(auth_app, name="auth")
app.add_typer(account_app, name="account")
app.add_typer(config_app, name="config")
app.add_typer(devices_app, name="devices")
app.add_typer(nodes_app, name="nodes")
app.add_typer(projects_app, name="projects")
app.add_typer(tasks_app, name="tasks")
app.add_typer(notes_app, name="notes")
app.add_typer(files_app, name="files")
app.add_typer(sync_app, name="sync")
app.add_typer(github_app, name="github")
app.add_typer(services_app, name="services")

# Compatibility cp command group
cp_app = typer.Typer(name="cp", help="Hosted control-plane operations (pairing across networks)")


@cp_app.command("set")
def cp_set(url: str = typer.Argument(..., help="Control plane URL")):
    """Point the CLI at the hosted control plane."""
    cfg = load_config()
    cfg.control_plane_url = url.rstrip("/")
    save_config(cfg)
    print_success(f"Control plane set to: [bold cyan]{cfg.control_plane_url}[/bold cyan]", title="Control Plane Set")


@cp_app.command("login")
def cp_login(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True),
):
    """Log in against the control plane."""
    cfg = load_config()
    base = (cfg.control_plane_url or "").rstrip("/")
    if not base:
        print_error("Control plane URL not configured. Set with 'nexus cp set <url>'.")
        raise typer.Exit(ExitCode.USAGE_ERROR)
    client = get_client(base_url=base)
    try:
        with status_spinner(f"Logging in to control plane at {base}…"):
            resp = client.post("/api/auth/login", json={"email": email, "password": password})
            tokens = resp.json()
            cfg.token = tokens.get("access_token")
            cfg.refresh_token = tokens.get("refresh_token")
            cfg.email = email
            save_config(cfg)
        print_success(f"Logged in as [bold cyan]{email}[/bold cyan] on control plane.", title="Control-plane Login")
    except NexusError as e:
        print_error(e.message, title="Control-plane Login Failed")
        raise typer.Exit(e.exit_code)


app.add_typer(cp_app, name="cp")


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit.", is_eager=True),
    json_output: bool = typer.Option(False, "--json", help="Output raw machine-readable JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose debug logging."),
) -> None:
    set_json_mode(json_output)
    if version:
        if json_output:
            output_json({"name": "nexus", "version": __version__})
        else:
            console.print(f"[bold cyan]nexus[/bold cyan] version [bold]{__version__}[/bold]")
        raise typer.Exit(ExitCode.SUCCESS)


# --- ROOT FIRST-CLASS COMMANDS ---


@app.command("doctor")
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Diagnose NEXUS CLI environment, configuration, connectivity, and dependencies."""
    doctor_cmd(json_output=json_output)


@app.command("version")
def version_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Show the NEXUS CLI version."""
    set_json_mode(json_output)
    if json_output:
        output_json({"name": "nexus", "version": __version__})
    else:
        console.print(f"[bold cyan]nexus[/bold cyan] version [bold]{__version__}[/bold]")


@app.command("init")
def init_cmd(url: str = typer.Option("http://127.0.0.1:8000", help="API Base URL")):
    """Initialize the NEXUS CLI with the backend server URL."""
    cfg = load_config()
    cfg.api_url = url.rstrip("/")
    save_config(cfg)
    console.print(Panel(f"API URL set to: [bold cyan]{cfg.api_url}[/bold cyan]", title="[bold green]NEXUS CLI Initialized[/bold green]", border_style="green", expand=False))


@app.command("status")
def status_cmd():
    """Check the connection to the NEXUS core node."""
    cfg = load_config()
    try:
        with status_spinner("Connecting to NEXUS Core..."):
            client = get_client()
            resp = client.get("/health", timeout=5)
            data = resp.json()
        auth_line = f"Logged in as [bold]{cfg.email}[/bold]" if cfg.token else "[yellow]Not logged in (run nexus login)[/yellow]"
        console.print(
            Panel(
                f"Connected to [bold]{data.get('service', 'NEXUS Node')}[/bold] (v{data.get('version', '?')})\n{auth_line}",
                title="[bold green]SUCCESS[/bold green]",
                border_style="green",
                expand=False,
            )
        )
    except Exception as e:
        console.print(
            Panel(
                f"Could not connect to NEXUS at {cfg.api_url}.\nIs the server running?\n[dim]{str(e)}[/dim]",
                title="[bold red]ERROR[/bold red]",
                border_style="red",
                expand=False,
            )
        )


@app.command("ui")
def launch_tui():
    """Launch the interactive NEXUS Full-Screen TUI."""
    try:
        from tui import NexusTUI
        tui_app = NexusTUI()
        tui_app.run()
    except ImportError as e:
        console.print(Panel(f"Could not load TUI module.\n[dim]{e}[/dim]", title="[bold red]ERROR[/bold red]", border_style="red", expand=False))


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query string"),
    path: Optional[str] = typer.Option(None, help="Directory path to search in"),
):
    """Search for text within files inside the storage roots."""
    from nexus_cli.commands.files import search_files
    search_files(query=query, path=path)


@app.command("bootstrap")
def bootstrap_cmd(
    mirror: str = typer.Option(
        "default",
        help="PyPI mirror: default | tuna | aliyun | ustc | sjtu | any https:// URL (QoL for slow links).",
    ),
    dry_run: bool = typer.Option(False, help="Show the plan without running anything."),
    venv_dir: Optional[str] = typer.Option(None, help="Custom venv location (default: ~/.nexus-venv)."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the interactive prompts (CI, scripted installs)."),
):
    """One-time setup: create the managed venv and install every pinned dependency."""
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.insert(0, str(_Path(__file__).resolve().parents[3] / "services" / "core-api"))
    try:
        from nexus_core.bootstrap import PIP_MIRRORS, plan_bootstrap, run_bootstrap
    except ImportError as e:
        console.print(Panel(f"Run from the repo (services/core-api not found).\n[dim]{e}[/dim]", title="[bold red]Bootstrap unavailable[/bold red]", border_style="red", expand=False))
        raise typer.Exit(1)

    if not yes:
        console.print(
            Panel(
                "This is the one-time NEXUS setup. I'll ask a few questions, then\n"
                "show the exact plan before anything runs on your machine.",
                title="[bold cyan]NEXUS first-run setup[/bold cyan]",
                border_style="cyan",
                expand=False,
            )
        )
        install_all = typer.confirm(
            "Install the full NEXUS stack now? (FastAPI node + CLI deps, pinned versions)",
            default=True,
        )
        if not install_all:
            console.print(
                Panel(
                    "Skipped the stack install.\n"
                    "Guidance: you can re-run [bold cyan]nexus bootstrap[/bold cyan] any time — nothing\n"
                    "partial was installed, and the plan is always shown before execution.",
                    title="[bold yellow]Setup deferred[/bold yellow]",
                    border_style="yellow",
                    expand=False,
                )
            )
            raise typer.Exit(0)
        if mirror == "default":
            slow_link = typer.confirm(
                "Is your PyPI link slow or unreliable? (choose a nearby mirror — helps a lot)",
                default=False,
            )
            if slow_link:
                console.print("[dim]Known mirrors:[/dim]")
                for name in ("tuna", "aliyun", "ustc", "sjtu"):
                    console.print(f"  [cyan]{name}[/cyan] — {PIP_MIRRORS[name]}")
                mirror = typer.prompt("Mirror to use (name or leave blank for default)", default="default")
        console.print(
            Panel(
                "Guidance while the install runs:\n"
                "• venv — a private Python environment in ~/.nexus-venv; nothing global is touched\n"
                "• uv — a faster installer the app uses automatically when present\n"
                "• everything runs as your user; no admin/sudo needed",
                title="[dim]What's happening[/dim]",
                border_style="dim",
                expand=False,
            )
        )

    try:
        plan = plan_bootstrap(
            venv_dir=_Path(venv_dir).expanduser() if venv_dir else None,
            mirror=mirror,
        )
    except ValueError as e:
        console.print(Panel(str(e), title="[bold red]Bad mirror[/bold red]", border_style="red", expand=False))
        raise typer.Exit(1)

    console.print(Panel(plan.describe(), title="[bold cyan]Setup plan[/bold cyan]", border_style="cyan", expand=False))
    if dry_run:
        console.print("[dim]--dry-run: nothing was executed[/dim]")
        return
    if not yes and not typer.confirm("Run this plan now?", default=True):
        console.print("[dim]Aborted — nothing was executed[/dim]")
        return
    console.print()
    ok = run_bootstrap(plan, echo=lambda line: console.print(f"[dim]{line}[/dim]"))
    if not ok:
        console.print(Panel("Setup failed — the lines above show the exact failing step.", title="[bold red]Setup failed[/bold red]", border_style="red", expand=False))
        raise typer.Exit(1)
    console.print(
        Panel(
            f"Environment ready.\n"
            f"Start the node (main server):\n"
            f"  [bold cyan]{plan.python_bin} -m uvicorn nexus_core.main:app --host 127.0.0.1 --port 8000[/bold cyan]\n"
            f"Then, from this CLI: [bold cyan]nexus node claim --name <machine>[/bold cyan]",
            title="[bold green]Setup complete[/bold green]",
            border_style="green",
            expand=False,
        )
    )


# --- ROOT LEGACY ALIASES (100% Backward Compatibility) ---


@app.command("login")
def legacy_login(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True),
):
    """Log in to the NEXUS Core and store credentials securely (legacy alias)."""
    from nexus_cli.commands.auth import login
    login(email=email, password=password, url=None)


@app.command("register")
def legacy_register(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True),
):
    """Register a new account on the NEXUS Core (legacy alias)."""
    from nexus_cli.commands.auth import register
    register(email=email, password=password, url=None)


@app.command("logout")
def legacy_logout():
    """Log out and remove credentials (legacy alias)."""
    from nexus_cli.commands.auth import logout
    logout()


@app.command("whoami")
def legacy_whoami():
    """Show the currently authenticated user (legacy alias)."""
    from nexus_cli.commands.auth import whoami
    whoami()


@app.command("devices")
def legacy_devices():
    """List registered devices (legacy alias)."""
    from nexus_cli.commands.devices import list_devices
    list_devices()


@app.command("device-token")
def legacy_device_token(
    platform_name: str = typer.Option("android", "--platform", "-p", help="Target platform (android | desktop | web)"),
    expires_minutes: int = typer.Option(10, "--expires", "-e", help="Token lifetime in minutes"),
):
    """Generate a one-time device pairing token (legacy alias)."""
    from nexus_cli.commands.devices import issue_device_token
    issue_device_token(platform_name=platform_name, expires_minutes=expires_minutes)


@app.command("node-claim")
def legacy_node_claim(
    name: str = typer.Option("My Node", help="Display name for this edge node"),
    platform: Optional[str] = typer.Option(None, help="Operating system (macos | windows | linux)"),
    endpoint: Optional[str] = typer.Option(None, help="Direct endpoint URL/host:port or leave blank for relay"),
    watch: bool = typer.Option(False, "--watch", help="Keep running in foreground and send heartbeats every 30s"),
    bridge: bool = typer.Option(True, "--bridge/--no-bridge", help="Run the secure outbound relay bridge"),
):
    """Claim this host machine as the authoritative NEXUS edge node (legacy alias)."""
    from nexus_cli.commands.nodes import claim_node
    claim_node(name=name, platform=platform, endpoint=endpoint, watch=watch, bridge=bridge)


@app.command("node-pair")
def legacy_node_pair():
    """Generate a 6-digit numeric pairing code for phone/tablet onboarding (legacy alias)."""
    from nexus_cli.commands.nodes import mint_pairing_code
    mint_pairing_code()


@app.command("node-resolve")
def legacy_node_resolve():
    """Resolve your active node address or relay route (legacy alias)."""
    from nexus_cli.commands.nodes import resolve_node
    resolve_node()


@app.command("node-list")
def legacy_node_list():
    """List all claimed nodes associated with your account (legacy alias)."""
    from nexus_cli.commands.nodes import list_nodes
    list_nodes()
