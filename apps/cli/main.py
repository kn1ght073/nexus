import typer
import warnings
warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")
import json as _json
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from typing import Optional
from config import load_config, save_config

app = typer.Typer(help="NEXUS CLI - Power Tools for the NEXUS Ecosystem")
project_app = typer.Typer(help="Manage projects")
task_app = typer.Typer(help="Manage tasks")
note_app = typer.Typer(help="Manage notes")
file_app = typer.Typer(help="Access files")


console = Console()
config = load_config()

# --- --json: machine-readable output for pipelines (plan §2.3) ---
JSON_MODE = {"enabled": False}


def output_json(data) -> None:
    """Print raw JSON when --json is set (single source of truth for all commands)."""
    if JSON_MODE["enabled"]:
        print(_json.dumps(data, indent=2, default=str))


def _set_json_mode(json_output: bool) -> None:
    JSON_MODE["enabled"] = json_output
    if json_output:
        # keep stdout clean for the JSON stream; rich writes to stderr
        import sys as _sys

        console.file = _sys.stderr


@app.callback()
def main_callback(
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of tables."
    ),
):
    """NEXUS CLI - Power Tools for the NEXUS Ecosystem"""
    _set_json_mode(json_output)


def _json_flag() -> bool:
    return typer.Option(False, "--json", help="Emit machine-readable JSON instead of tables.")


app.add_typer(project_app, name="project")
app.add_typer(task_app, name="task")
app.add_typer(note_app, name="note")
app.add_typer(file_app, name="file")


def get_headers() -> dict:
    """Auth headers from the stored login token (real JWT since core v0.2.0)."""
    headers = {}
    if config.token:
        headers["Authorization"] = f"Bearer {config.token}"
    return headers


def require_login() -> bool:
    """Check that a token is stored before hitting protected endpoints."""
    if not config.token:
        console.print(
            Panel(
                "No stored login. Run [bold cyan]nexus login[/bold cyan] first.",
                title="[bold red]Authentication required[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        return False
    return True


# --- AUTH ---
@app.command()
def init(url: str = typer.Option("http://127.0.0.1:8000", help="API Base URL")):
    """Initialize the NEXUS CLI with the backend server URL."""
    config.api_url = url.rstrip("/")
    save_config(config)
    console.print(Panel(f"API URL set to: [bold cyan]{config.api_url}[/bold cyan]", title="[bold green]NEXUS CLI Initialized[/bold green]", border_style="green", expand=False))


@app.command()
def login(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True),
):
    """Log in to the NEXUS Core and store the token."""
    try:
        with console.status("[bold cyan]Authenticating...[/bold cyan]"):
            response = requests.post(
                f"{config.api_url}/api/auth/login",
                json={"email": email, "password": password},
                timeout=5,
            )
        if response.status_code == 401:
            console.print(Panel("Invalid email or password.", title="[bold red]Login failed[/bold red]", border_style="red", expand=False))
            raise typer.Exit(1)
        response.raise_for_status()
        tokens = response.json()

        config.token = tokens["access_token"]
        config.refresh_token = tokens.get("refresh_token")
        config.email = email
        save_config(config)
        console.print(Panel(f"Logged in as [bold cyan]{email}[/bold cyan].", title="[bold green]Login successful[/bold green]", border_style="green", expand=False))
    except requests.exceptions.RequestException as e:
        console.print(Panel(f"Could not reach NEXUS at {config.api_url}.\n[dim]{e}[/dim]", title="[bold red]Login failed[/bold red]", border_style="red", expand=False))


@app.command()
def register(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
):
    """Create a new NEXUS account (password must be 8+ characters)."""
    if len(password) < 8:
        console.print(Panel("Password must be at least 8 characters.", title="[bold red]Registration failed[/bold red]", border_style="red", expand=False))
        raise typer.Exit(1)
    try:
        with console.status("[bold cyan]Registering...[/bold cyan]"):
            response = requests.post(
                f"{config.api_url}/api/auth/register",
                json={"email": email, "password": password},
                timeout=5,
            )
        if response.status_code == 409:
            console.print(Panel("Email already registered. Try [bold cyan]nexus login[/bold cyan].", title="[bold red]Registration failed[/bold red]", border_style="red", expand=False))
            raise typer.Exit(1)
        response.raise_for_status()
        console.print(Panel(f"Account created. Now run [bold cyan]nexus login[/bold cyan].", title="[bold green]Registration successful[/bold green]", border_style="green", expand=False))
    except requests.exceptions.RequestException as e:
        console.print(Panel(f"Could not reach NEXUS at {config.api_url}.\n[dim]{e}[/dim]", title="[bold red]Registration failed[/bold red]", border_style="red", expand=False))


@app.command()
def logout():
    """Forget the stored credentials."""
    config.token = None
    config.refresh_token = None
    config.email = None
    save_config(config)
    console.print(Panel("Credentials cleared.", title="[bold green]Logged out[/bold green]", border_style="green", expand=False))


@app.command()
def whoami():
    """Show the account tied to the stored token."""
    if not require_login():
        return
    try:
        response = requests.get(f"{config.api_url}/api/auth/me", headers=get_headers(), timeout=5)
        response.raise_for_status()
        me = response.json()
        console.print(Panel(f"[bold]{me['email']}[/bold] (user #{me['id']}, since {me['created_at'][:10]})", title="Who am I", border_style="cyan", expand=False))
    except requests.exceptions.RequestException as e:
        console.print(Panel(str(e), title="[bold red]Error[/bold red]", border_style="red", expand=False))


@app.command("ui")
def launch_tui():
    """Launch the interactive NEXUS Full-Screen TUI."""
    try:
        from tui import NexusTUI
        tui_app = NexusTUI()
        tui_app.run()
    except ImportError as e:
        console.print(Panel(f"Could not load TUI module.\n[dim]{e}[/dim]", title="[bold red]ERROR[/bold red]", border_style="red", expand=False))


# --- BOOTSTRAP (one-time setup, all inside the app) ---
@app.command()
def bootstrap(
    mirror: str = typer.Option(
        "default",
        help="PyPI mirror: default | tuna | aliyun | ustc | sjtu | any https:// URL (QoL for slow links).",
    ),
    dry_run: bool = typer.Option(False, help="Show the plan without running anything."),
    venv_dir: str = typer.Option(None, help="Custom venv location (default: ~/.nexus-venv)."),
):
    """One-time setup: create the managed venv and install every pinned dependency.

    Uses uv automatically when available (fast), falls back to plain
    python -m venv + pip otherwise. No manual pip/uv/venv steps — the app
    sets itself up and tells you the exact command to start the node.
    """
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "services" / "core-api"))
    try:
        from nexus_core.bootstrap import plan_bootstrap, run_bootstrap
    except ImportError as e:
        console.print(Panel(f"Run from the repo (services/core-api not found).\n[dim]{e}[/dim]", title="[bold red]Bootstrap unavailable[/bold red]", border_style="red", expand=False))
        raise typer.Exit(1)

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


@app.command()
def status():
    """Check the connection to the NEXUS core node."""
    try:
        with console.status("[bold cyan]Connecting to NEXUS Core...[/bold cyan]"):
            response = requests.get(f"{config.api_url}/health", timeout=5)
            response.raise_for_status()
            data = response.json()
        auth_line = f"Logged in as [bold]{config.email}[/bold]" if config.token else "[yellow]Not logged in (run nexus login)[/yellow]"
        console.print(Panel(f"Connected to [bold]{data.get('service', 'NEXUS Node')}[/bold] (v{data.get('version', '?')})\n{auth_line}", title="[bold green]SUCCESS[/bold green]", border_style="green", expand=False))
    except requests.exceptions.RequestException as e:
        console.print(Panel(f"Could not connect to NEXUS at {config.api_url}.\nIs the server running?\n[dim]{str(e)}[/dim]", title="[bold red]ERROR[/bold red]", border_style="red", expand=False))


# --- PROJECTS ---
@project_app.command("list")
def list_projects(json_output: bool = _json_flag()):
    """List all projects."""
    _set_json_mode(json_output)
    if not require_login():
        return
    try:
        with console.status("[bold cyan]Fetching projects...[/bold cyan]"):
            response = requests.get(f"{config.api_url}/api/projects", headers=get_headers())
            response.raise_for_status()
            projects = response.json()
        output_json(projects)
        if JSON_MODE["enabled"]:
            return

        table = Table(title="[bold]NEXUS Projects[/bold]", box=box.ROUNDED, header_style="bold cyan")
        table.add_column("ID", justify="right", style="dim", width=4)
        table.add_column("Title")
        table.add_column("Status")

        for p in projects:
            status_icon = "⏳ Pending" if p.get("status") != "completed" else "✅ Completed"
            status_color = "yellow" if p.get("status") != "completed" else "green"
            table.add_row(str(p["id"]), p["title"], f"[{status_color}]{status_icon}[/{status_color}]")

        console.print(table)
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error fetching projects[/bold red]", border_style="red", expand=False))


@project_app.command("create")
def create_project(title: str, description: str = ""):
    """Create a new project."""
    if not require_login():
        return
    try:
        with console.status("[bold cyan]Creating project...[/bold cyan]"):
            payload = {"title": title, "description": description}
            response = requests.post(f"{config.api_url}/api/projects", json=payload, headers=get_headers())
            response.raise_for_status()
            p = response.json()
        console.print(Panel(f"Title: [bold]{p['title']}[/bold]\nDesc: [dim]{p.get('description', '')}[/dim]", title=f"[bold green]Project Created (ID: {p['id']})[/bold green]", border_style="green", expand=False))
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error creating project[/bold red]", border_style="red", expand=False))


# --- TASKS ---
def _render_tasks_table(tasks: list):
    table = Table(title="[bold]NEXUS Tasks[/bold]", box=box.ROUNDED, header_style="bold magenta")
    table.add_column("ID", justify="right", style="dim", width=4)
    table.add_column("Title")
    table.add_column("Project", justify="right", style="cyan")
    table.add_column("Status")
    for t in tasks:
        # status field comes from the API (fixes the old is_completed bug)
        status = t.get("status", "pending")
        icon = {"completed": "✅ Done", "in_progress": "🔄 In Progress"}.get(status, "⏳ Pending")
        color = {"completed": "green", "in_progress": "blue"}.get(status, "yellow")
        table.add_row(str(t["id"]), t["title"], str(t.get("project_id", "-")), f"[{color}]{icon}[/{color}]")
    console.print(table)


@task_app.command("list")
def list_tasks(json_output: bool = _json_flag()):
    """List all tasks."""
    _set_json_mode(json_output)
    if not require_login():
        return
    try:
        with console.status("[bold cyan]Fetching tasks...[/bold cyan]"):
            response = requests.get(f"{config.api_url}/api/tasks", headers=get_headers())
            response.raise_for_status()
            tasks = response.json()
        output_json(tasks)
        if JSON_MODE["enabled"]:
            return
        _render_tasks_table(tasks)
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error fetching tasks[/bold red]", border_style="red", expand=False))


@task_app.command("add")
def add_task(title: str, project_id: int = typer.Argument(None)):
    """Add a new task (optionally to a project)."""
    if not require_login():
        return
    try:
        with console.status("[bold cyan]Adding task...[/bold cyan]"):
            payload = {"title": title}
            if project_id:
                payload["project_id"] = project_id
            response = requests.post(f"{config.api_url}/api/tasks", json=payload, headers=get_headers())
            response.raise_for_status()
            t = response.json()
        console.print(Panel(f"Title: [bold]{t['title']}[/bold]\nProject ID: {t.get('project_id', '-')}", title=f"[bold green]Task Added (ID: {t['id']})[/bold green]", border_style="green", expand=False))
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error adding task[/bold red]", border_style="red", expand=False))


@task_app.command("today")
def today_tasks(json_output: bool = _json_flag()):
    """Show tasks created today."""
    _set_json_mode(json_output)
    if not require_login():
        return
    try:
        with console.status("[bold cyan]Fetching today's tasks...[/bold cyan]"):
            response = requests.get(f"{config.api_url}/api/tasks/today", headers=get_headers())
            response.raise_for_status()
            tasks = response.json()
        output_json(tasks)
        if JSON_MODE["enabled"]:
            return
        _render_tasks_table(tasks)
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error fetching today's tasks[/bold red]", border_style="red", expand=False))


@task_app.command("done")
def done_task(task_id: int):
    """Mark a task as completed."""
    if not require_login():
        return
    try:
        with console.status("[bold cyan]Completing task...[/bold cyan]"):
            response = requests.post(f"{config.api_url}/api/tasks/{task_id}/done", headers=get_headers())
            response.raise_for_status()
            t = response.json()
        console.print(Panel(f"[bold]{t['title']}[/bold] → ✅ Completed", title="[bold green]Task Completed[/bold green]", border_style="green", expand=False))
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error completing task[/bold red]", border_style="red", expand=False))


# --- NOTES ---
@note_app.command("add")
def add_note(title: str, content: str):
    """Add a quick note."""
    if not require_login():
        return
    try:
        with console.status("[bold cyan]Saving note...[/bold cyan]"):
            payload = {"title": title, "content": content}
            response = requests.post(f"{config.api_url}/api/notes", json=payload, headers=get_headers())
            response.raise_for_status()
            n = response.json()
        console.print(Panel(f"[dim]{n.get('content', '')}[/dim]", title=f"[bold blue]Note Saved: {n['title']} (ID: {n['id']})[/bold blue]", border_style="blue", expand=False))
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error adding note[/bold red]", border_style="red", expand=False))


@note_app.command("list")
def list_notes(json_output: bool = _json_flag()):
    """List saved notes."""
    _set_json_mode(json_output)
    if not require_login():
        return
    try:
        with console.status("[bold cyan]Fetching notes...[/bold cyan]"):
            response = requests.get(f"{config.api_url}/api/notes", headers=get_headers())
            response.raise_for_status()
            notes = response.json()
        output_json(notes)
        if JSON_MODE["enabled"]:
            return
        table = Table(title="[bold]NEXUS Notes[/bold]", box=box.ROUNDED, header_style="bold blue")
        table.add_column("ID", justify="right", style="dim", width=4)
        table.add_column("Title")
        table.add_column("Preview")
        for n in notes:
            preview = (n.get("content") or "")[:40] + ("..." if len(n.get("content") or "") > 40 else "")
            table.add_row(str(n["id"]), n["title"], preview)
        console.print(table)
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error fetching notes[/bold red]", border_style="red", expand=False))


# --- FILES ---
@file_app.command("list")
def list_files(path: str = typer.Argument(None, help="Directory path to browse"), json_output: bool = _json_flag()):
    """List files in a storage root (defaults to the configured root)."""
    _set_json_mode(json_output)
    if not require_login():
        return
    try:
        with console.status(f"[bold cyan]Browsing files{' in '+path if path else ''}...[/bold cyan]"):
            params = {"path": path} if path else {}
            response = requests.get(f"{config.api_url}/api/files/browse", params=params, headers=get_headers())
            response.raise_for_status()
            files = response.json()
        output_json(files)
        if JSON_MODE["enabled"]:
            return

        table = Table(title=f"[bold]NEXUS Files[/bold]", box=box.ROUNDED, header_style="bold yellow")
        table.add_column("Type", width=4)
        table.add_column("Name")
        table.add_column("Size (bytes)", justify="right")

        for f in files:
            icon = "📁" if f["is_dir"] else "📄"
            size_str = str(f["size"]) if not f["is_dir"] else "-"
            table.add_row(icon, f["name"], size_str)

        console.print(table)
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error browsing files[/bold red]", border_style="red", expand=False))


@file_app.command("roots")
def show_roots(json_output: bool = _json_flag()):
    """Show the server's configured storage roots (the file jail)."""
    _set_json_mode(json_output)
    if not require_login():
        return
    try:
        response = requests.get(f"{config.api_url}/api/files/roots", headers=get_headers(), timeout=5)
        response.raise_for_status()
        roots = response.json()
        console.print(Panel("\n".join(f"• [cyan]{r}[/cyan]" for r in roots) or "(none)", title="Storage Roots", border_style="yellow", expand=False))
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error[/bold red]", border_style="red", expand=False))


# --- SEARCH ---
@app.command("search")
def search(query: str, path: str = typer.Option(None, help="Directory path to search in"), json_output: bool = _json_flag()):
    """Search for text within files inside the storage roots."""
    _set_json_mode(json_output)
    if not require_login():
        return
    try:
        with console.status(f"[bold cyan]Searching for '{query}'...[/bold cyan]"):
            params = {"query": query}
            if path:
                params["path"] = path
            response = requests.get(f"{config.api_url}/api/files/search", params=params, headers=get_headers())
            response.raise_for_status()
            results = response.json()
        output_json(results)
        if JSON_MODE["enabled"]:
            return

        if not results:
            console.print(Panel(f"No results found for '{query}'", title="[bold yellow]Search Empty[/bold yellow]", border_style="yellow", expand=False))
            return

        table = Table(title=f"[bold]Search Results for '{query}'[/bold]", box=box.ROUNDED, header_style="bold green")
        table.add_column("File Path", style="cyan")
        table.add_column("Match Context")

        for r in results:
            table.add_row(r["path"], r["match_context"])

        console.print(table)
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error searching files[/bold red]", border_style="red", expand=False))


# --- DEVICES ---
@app.command()
def devices(json_output: bool = _json_flag()):
    """List registered devices."""
    _set_json_mode(json_output)
    if not require_login():
        return
    try:
        response = requests.get(f"{config.api_url}/api/devices", headers=get_headers(), timeout=5)
        response.raise_for_status()
        device_list = response.json()
        output_json(device_list)
        if JSON_MODE["enabled"]:
            return
        if not device_list:
            console.print(Panel("No devices registered yet.", title="NEXUS Devices", border_style="yellow", expand=False))
            return
        table = Table(title="[bold]NEXUS Devices[/bold]", box=box.ROUNDED, header_style="bold cyan")
        table.add_column("ID", justify="right", style="dim", width=4)
        table.add_column("Name")
        table.add_column("Platform")
        table.add_column("Online")
        table.add_column("Capabilities")
        for d in device_list:
            online = "[green]●[/green]" if d.get("is_online") else "[dim]○[/dim]"
            caps = ", ".join(d.get("capabilities", [])) or "-"
            table.add_row(str(d["id"]), d["name"], d.get("platform", "-"), online, caps)
        console.print(table)
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error fetching devices[/bold red]", border_style="red", expand=False))


# --- SYNC (step 3) ---
@app.command()
def sync(
    since: str = typer.Option(
        None, help="ISO timestamp of the last pull; omit for a full first pull."
    ),
    json_output: bool = _json_flag()
):
    """Pull server changes (projects/tasks/notes) since a cursor."""
    _set_json_mode(json_output)
    if not require_login():
        return
    try:
        payload = {"since": since} if since else {}
        response = requests.post(
            f"{config.api_url}/api/sync/pull", json=payload, headers=get_headers(), timeout=10
        )
        response.raise_for_status()
        body = response.json()
        changes = body["changes"]
        output_json(body)
        counts = {k: len(v) for k, v in changes.items()}
        total = sum(counts.values())
        if JSON_MODE["enabled"]:
            return
        lines = "\n".join(
            f"[cyan]{kind}[/cyan]: {counts[kind]} change(s)" for kind in ("projects", "tasks", "notes")
        )
        console.print(
            Panel(
                lines + f"\nServer time: [dim]{body['server_time']}[/dim]",
                title=f"[bold green]Sync pull complete ({total} change(s))[/bold green]",
                border_style="green",
                expand=False,
            )
        )
        for t in changes["tasks"]:
            deleted = t.get("deleted_at") is not None
            mark = "[red]✝ deleted[/red]" if deleted else f"rev {t['revision']}"
            console.print(f"  • task #{t['id']} [bold]{t['title']}[/bold] ({mark})")
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Sync failed[/bold red]", border_style="red", expand=False))


# --- DEVICE (step 3) ---
device_app = typer.Typer(help="Manage devices & device tokens")


app.add_typer(device_app, name="device")


@device_app.command("token")
def device_token(
    device_id: int,
    scopes: str = typer.Option(
        "read", help="Comma-separated scopes (subset of the device's capabilities)."
    ),
    json_output: bool = _json_flag()
):
    """Issue a scoped token bound to one of your devices (admin action)."""
    _set_json_mode(json_output)
    if not require_login():
        return
    try:
        response = requests.post(
            f"{config.api_url}/api/devices/{device_id}/token",
            json={"scopes": [s.strip() for s in scopes.split(",") if s.strip()]},
            headers=get_headers(),
            timeout=5,
        )
        if response.status_code == 400:
            console.print(Panel(response.json().get("detail", "invalid scopes"), title="[bold red]Invalid scopes[/bold red]", border_style="red", expand=False))
            raise typer.Exit(1)
        response.raise_for_status()
        body = response.json()
        output_json(body)
        console.print(
            Panel(
                f"scope: [bold cyan]{body['scope']}[/bold cyan]\n[dim]Store this token on the device; it is not saved by the CLI.[/dim]",
                title=f"[bold green]Device token for device #{body['device_id']}[/bold green]",
                border_style="green",
                expand=False,
            )
        )
    except typer.Exit:
        raise
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error issuing token[/bold red]", border_style="red", expand=False))


# --- CONTROL PLANE (step 8: log in from anywhere) ---
cp_app = typer.Typer(help="Control-plane (hosted) account & node coordination")
node_app = typer.Typer(help="Manage this machine's node registration")
app.add_typer(cp_app, name="cp")
app.add_typer(node_app, name="node")


def _cp_headers() -> dict:
    """Auth headers against the control plane (stored token works for both)."""
    h = get_headers()
    if config.control_plane_url:
        h["X-Nexus-Node-Key"] = config.node_api_key or ""
    return h


def _cp_url() -> str:
    if not config.control_plane_url:
        console.print(
            Panel(
                "No control plane configured.\nRun [bold cyan]nexus cp set <url>[/bold cyan] first "
                "(e.g. https://nexus-control.onrender.com).",
                title="[bold red]Control plane not configured[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        return ""
    return config.control_plane_url.rstrip("/")


@cp_app.command("set")
def cp_set(url: str):
    """Point the CLI at the hosted control plane (Render URL)."""
    config.control_plane_url = url.rstrip("/")
    save_config(config)
    console.print(
        Panel(f"Control plane: [bold cyan]{config.control_plane_url}[/bold cyan]", title="[bold green]Control plane set[/bold green]", border_style="green", expand=False)
    )


@cp_app.command("login")
def cp_login(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True),
):
    """Log in against the control plane (works from anywhere)."""
    base = _cp_url()
    if not base:
        return
    try:
        response = requests.post(f"{base}/api/auth/login", json={"email": email, "password": password}, timeout=10)
        if response.status_code == 401:
            console.print(Panel("Invalid email or password.", title="[bold red]Login failed[/bold red]", border_style="red", expand=False))
            raise typer.Exit(1)
        response.raise_for_status()
        tokens = response.json()
        config.token = tokens["access_token"]
        config.refresh_token = tokens.get("refresh_token")
        config.email = email
        save_config(config)
        health = requests.get(f"{base}/health", timeout=10).json()
        console.print(
            Panel(
                f"Logged in as [bold cyan]{email}[/bold cyan] (mode: {health.get('mode', '?')})\n"
                "[dim]The control plane stores accounts + node registry only — "
                "personal data lives on your node.[/dim]",
                title="[bold green]Control-plane login successful[/bold green]",
                border_style="green",
                expand=False,
            )
        )
    except requests.exceptions.RequestException as e:
        console.print(Panel(f"Could not reach {base}.\n[dim]{e}[/dim]", title="[bold red]Login failed[/bold red]", border_style="red", expand=False))


@node_app.command("claim")
def node_claim(
    name: str = typer.Option("My Node", help="Display name for this machine."),
    platform: str = typer.Option(None, help="macos | windows | linux (auto-detected if omitted)."),
    endpoint: str = typer.Option(None, help="How clients reach this node (host:port / Tailscale name / tunnel URL)."),
    watch: bool = typer.Option(False, help="Stay in the foreground and heartbeat every 30s."),
    bridge: bool = typer.Option(True, help="Also start the secure relay bridge (no open ports; phone can attach from anywhere)."),
):
    """Register this machine as the active NEXUS node (main server)."""
    base = _cp_url()
    if not base:
        return
    if not config.token:
        console.print(Panel("Run [bold cyan]nexus cp login[/bold cyan] first.", title="[bold red]Not logged in[/bold red]", border_style="red", expand=False))
        return
    if platform is None:
        import platform as _p

        platform = {"Darwin": "macos", "Windows": "windows"}.get(_p.system(), "linux")
    try:
        response = requests.post(
            f"{base}/api/nodes/claim",
            json={"name": name, "platform": platform, "endpoint": endpoint},
            headers=_cp_headers(),
            timeout=10,
        )
        response.raise_for_status()
        node = response.json()
        config.node_id = node["id"]
        config.node_api_key = node["api_key"]
        save_config(config)
        # standalone bridge config: python -m nexus_core.node_bridge reads this
        import json as _j
        from pathlib import Path as _Path

        _Path("nexus_node.json").write_text(
            _j.dumps({
                "control_plane_url": base,
                "node_id": node["id"],
                "api_key": node["api_key"],
            }, indent=2), encoding="utf-8",
        )
        console.print(
            Panel(
                f"Node [bold cyan]{node['name']}[/bold cyan] (#{node['id']}) is now the [bold green]active main server[/bold green].\n"
                f"[dim]api_key stored in ~/.nexus-cli.json — keep it private.[/dim]\n"
                + ("[dim]bridge config written to nexus_node.json[/dim]" if bridge else ""),
                title="[bold green]Node claimed[/bold green]",
                border_style="green",
                expand=False,
            )
        )
        if watch:
            import time

            console.print("[dim]heartbeating every 30s — Ctrl-C to stop[/dim]")
            while True:
                try:
                    requests.post(f"{base}/api/nodes/{config.node_id}/heartbeat", headers=_cp_headers(), timeout=10)
                    console.print("[dim]♥ heartbeat[/dim]")
                except requests.exceptions.RequestException:
                    console.print("[red]heartbeat failed (offline?) — retrying[/red]")
                time.sleep(30)
        elif bridge:
            _run_bridge_foreground(base, node)
    except requests.exceptions.RequestException as e:
        console.print(Panel(str(e), title="[bold red]Claim failed[/bold red]", border_style="red", expand=False))


def _run_bridge_foreground(base: str, node: dict) -> None:
    """Run the secure relay bridge (outbound WS to the control plane) until Ctrl-C."""
    console.print(
        Panel(
            "Starting the secure bridge: this machine opens ONE outbound connection to the "
            "control plane. No inbound ports, no port forwarding, no public exposure. "
            "Pair your phone with [bold cyan]nexus node pair[/bold cyan] (on any machine logged in as you) "
            "and it can reach this node from anywhere.",
            title="[bold green]Secure bridge[/bold green]",
            border_style="green",
            expand=False,
        )
    )
    try:
        import asyncio

        import sys as _sys
        from pathlib import Path as _Path

        _sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "services" / "core-api"))
        from nexus_core.node_bridge import NodeBridge
        from nexus_core.main import app as _core_app  # the full node app to serve relayed calls

        async def _go():
            b = NodeBridge(base, node["id"], node["api_key"], app=_core_app)
            await b.run()

        asyncio.run(_go())
    except KeyboardInterrupt:
        console.print("[dim]bridge stopped[/dim]")
    except ImportError as e:
        console.print(
            Panel(
                f"The bridge needs the core-api package on sys.path (run from the repo).\n[dim]{e}[/dim]",
                title="[bold red]Bridge unavailable[/bold red]",
                border_style="red",
                expand=False,
            )
        )


@node_app.command("pair")
def node_pair(json_output: bool = _json_flag()):
    """Mint a pairing code: type it into the phone/desktop app to link it to this node (secure relay, no open ports)."""
    _set_json_mode(json_output)
    base = _cp_url()
    if not base:
        return
    if not config.token:
        console.print(Panel("Run [bold cyan]nexus cp login[/bold cyan] first.", title="[bold red]Not logged in[/bold red]", border_style="red", expand=False))
        return
    try:
        response = requests.post(
            f"{base}/api/relay/pair",
            json={"device_name": "phone"},
            headers=_cp_headers(),
            timeout=10,
        )
        response.raise_for_status()
        body = response.json()
        output_json(body)
        console.print(
            Panel(
                f"[bold green]{body['code']}[/bold green]\n"
                f"[dim]valid until {body['expires_at']}[/dim]\n"
                "Enter this code in the NEXUS app on the device you want to link. "
                "The connection runs through the control plane over an end-to-end "
                "encrypted relay — your machine opens no ports.",
                title="[bold green]Pairing code[/bold green]",
                border_style="green",
                expand=False,
            )
        )
    except requests.exceptions.RequestException as e:
        console.print(Panel(str(e), title="[bold red]Pairing failed[/bold red]", border_style="red", expand=False))


@node_app.command("resolve")
def node_resolve(json_output: bool = _json_flag()):
    """Show the currently active node (where personal data is served from)."""
    _set_json_mode(json_output)
    base = _cp_url()
    if not base:
        return
    if not config.token:
        console.print(Panel("Run [bold cyan]nexus cp login[/bold cyan] first.", title="[bold red]Not logged in[/bold red]", border_style="red", expand=False))
        return
    try:
        response = requests.get(f"{base}/api/nodes/active", headers=_cp_headers(), timeout=10)
        response.raise_for_status()
        node = response.json()
        output_json(node)
        if JSON_MODE["enabled"]:
            return
        if node is None:
            console.print(
                Panel(
                    "No active node online.\n[dim]Start one with [bold cyan]nexus node claim --watch[/bold cyan] "
                    "on your Mac/Windows machine.[/dim]",
                    title="[bold yellow]No active node[/bold yellow]",
                    border_style="yellow",
                    expand=False,
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold green]{node['name']}[/bold green] ({node['platform']}) at {node.get('endpoint') or 'unknown endpoint'}\n"
                    f"[dim]services: {node.get('services') or {}} · last seen {node['last_seen']}[/dim]",
                    title="Active node",
                    border_style="green",
                    expand=False,
                )
            )
    except requests.exceptions.RequestException as e:
        console.print(Panel(str(e), title="[bold red]Resolve failed[/bold red]", border_style="red", expand=False))


@node_app.command("list")
def node_list(json_output: bool = _json_flag()):
    """List all registered nodes with liveness."""
    _set_json_mode(json_output)
    base = _cp_url()
    if not base:
        return
    try:
        response = requests.get(f"{base}/api/nodes", headers=_cp_headers(), timeout=10)
        response.raise_for_status()
        nodes = response.json()
        output_json(nodes)
        if not nodes:
            console.print(Panel("No nodes registered yet.", title="Nodes", border_style="cyan", expand=False))
            return
        table = Table(title="[bold]NEXUS Nodes[/bold]", box=box.ROUNDED, header_style="bold cyan")
        table.add_column("ID", width=4)
        table.add_column("Name")
        table.add_column("Platform")
        table.add_column("Active")
        table.add_column("Online")
        for n in nodes:
            table.add_row(str(n["id"]), n["name"], n["platform"], "★" if n["is_active"] else "", "●" if n["is_online"] else "○")
        console.print(table)
    except requests.exceptions.RequestException as e:
        console.print(Panel(str(e), title="[bold red]Error fetching nodes[/bold red]", border_style="red", expand=False))


# --- NODE SERVICES (installable on the node) ---
services_app = typer.Typer(help="Install/inspect optional node services (stt, ...)")
app.add_typer(services_app, name="services")


@services_app.command("status")
def services_status(json_output: bool = _json_flag()):
    """Show which optional services this machine's node has installed."""
    _set_json_mode(json_output)
    if config.node_id and config.control_plane_url:
        try:
            response = requests.get(
                f"{config.control_plane_url.rstrip('/')}/api/nodes", headers=_cp_headers(), timeout=10
            )
            response.raise_for_status()
            mine = [n for n in response.json() if n["id"] == config.node_id]
            services = mine[0]["services"] if mine else {}
        except requests.exceptions.RequestException:
            services = {}
    else:
        services = _detect_local_services()
    output_json(services)
    rows = "\n".join(f"[cyan]{k}[/cyan]: {v}" for k, v in services.items()) or "[dim]none installed[/dim]"
    console.print(Panel(rows, title="Node services", border_style="cyan", expand=False))


def _detect_local_services() -> dict:
    """Probe the local machine for installable services (no network)."""
    services = {}
    try:
        import faster_whisper  # noqa: F401

        services["stt"] = "faster-whisper"
    except ImportError:
        pass
    try:
        import requests as _r  # noqa: F401

        try:
            _r.get("http://127.0.0.1:11434/api/version", timeout=0.5)
            services["llm"] = "ollama"
        except Exception:
            pass
    except ImportError:
        pass
    return services


@services_app.command("install")
def services_install(
    service: str = typer.Argument(..., help="Service to install: stt | llm | bootstrap (full environment setup)"),
    mirror: str = typer.Option(
        "default",
        help="PyPI mirror for this install: default | tuna | aliyun | ustc | sjtu | https:// URL.",
    ),
):
    """Install an optional service on this machine (the main node)."""
    if service == "bootstrap":
        # full environment self-setup — same engine as `nexus bootstrap`
        import sys as _sys
        from pathlib import Path as _Path

        _sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "services" / "core-api"))
        from nexus_core.bootstrap import plan_bootstrap, run_bootstrap

        try:
            plan = plan_bootstrap(mirror=mirror)
        except ValueError as e:
            console.print(Panel(str(e), title="[bold red]Bad mirror[/bold red]", border_style="red", expand=False))
            raise typer.Exit(1)
        console.print(Panel(plan.describe(), title="[bold cyan]Setup plan[/bold cyan]", border_style="cyan", expand=False))
        if not run_bootstrap(plan, echo=lambda line: console.print(f"[dim]{line}[/dim]")):
            console.print(Panel("Setup failed — see the failing step above.", title="[bold red]Setup failed[/bold red]", border_style="red", expand=False))
            raise typer.Exit(1)
        console.print(Panel(f"Environment ready. Node start command:\n  {plan.python_bin} -m uvicorn nexus_core.main:app", title="[bold green]Setup complete[/bold green]", border_style="green", expand=False))
        return
    if service == "stt":
        console.print(Panel("Installing [bold cyan]faster-whisper[/bold cyan] (reliable local transcription)…", border_style="cyan", expand=False))
        import subprocess
        import sys

        result = subprocess.run([sys.executable, "-m", "pip", "install", "faster-whisper"])
        if result.returncode != 0:
            console.print(Panel("pip failed — see output above.", title="[bold red]Install failed[/bold red]", border_style="red", expand=False))
            raise typer.Exit(1)
        console.print(Panel("faster-whisper installed.\n[dim]Model weights download on first use (base ≈ 150MB).[/dim]", title="[bold green]STT installed[/bold green]", border_style="green", expand=False))
    elif service == "llm":
        console.print(
            Panel(
                "Ollama is a native app, not a pip package.\n"
                "Install from https://ollama.com/download then:\n"
                "  ollama pull llama3.2\n"
                "The node auto-detects it at http://127.0.0.1:11434.",
                title="Install Ollama (manual)",
                border_style="cyan",
                expand=False,
            )
        )
    else:
        console.print(Panel(f"Unknown service '{service}'. Available: stt, llm.", title="[bold red]Unknown service[/bold red]", border_style="red", expand=False))
        raise typer.Exit(1)

    # report to the control plane if this machine is a claimed node
    if config.node_id and config.control_plane_url:
        detected = _detect_local_services()
        try:
            requests.post(
                f"{config.control_plane_url.rstrip('/')}/api/nodes/{config.node_id}/services",
                json={"services": detected},
                headers=_cp_headers(),
                timeout=10,
            )
        except requests.exceptions.RequestException:
            pass


if __name__ == "__main__":
    app()
