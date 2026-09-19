import typer
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
from typing import Optional
from config import load_config, save_config

app = typer.Typer(help="NEXUS CLI - Power Tools for the NEXUS Ecosystem")
project_app = typer.Typer(help="Manage projects")
task_app = typer.Typer(help="Manage tasks")
note_app = typer.Typer(help="Manage notes")

app.add_typer(project_app, name="project")
app.add_typer(task_app, name="task")
app.add_typer(note_app, name="note")

console = Console()
config = load_config()

def get_headers():
    return {"Authorization": "Bearer mock-token-123"}

@app.command()
def init(url: str = typer.Option("http://127.0.0.1:8000", help="API Base URL")):
    """Initialize the NEXUS CLI with the backend server URL."""
    config.api_url = url.rstrip("/")
    save_config(config)
    console.print(Panel(f"API URL set to: [bold cyan]{config.api_url}[/bold cyan]", title="[bold green]NEXUS CLI Initialized[/bold green]", border_style="green", expand=False))

@app.command()
def status():
    """Check the connection to the NEXUS core node."""
    try:
        with console.status("[bold cyan]Connecting to NEXUS Core...[/bold cyan]"):
            response = requests.get(f"{config.api_url}/health", timeout=5)
            response.raise_for_status()
            data = response.json()
        console.print(Panel(f"Connected to [bold]{data.get('service', 'NEXUS Node')}[/bold]", title="[bold green]SUCCESS[/bold green]", border_style="green", expand=False))
    except requests.exceptions.RequestException as e:
        console.print(Panel(f"Could not connect to NEXUS at {config.api_url}.\nIs the server running?\n[dim]{str(e)}[/dim]", title="[bold red]ERROR[/bold red]", border_style="red", expand=False))

# --- PROJECTS ---
@project_app.command("list")
def list_projects():
    """List all projects."""
    try:
        with console.status("[bold cyan]Fetching projects...[/bold cyan]"):
            response = requests.get(f"{config.api_url}/api/projects", headers=get_headers())
            response.raise_for_status()
            projects = response.json()
        
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
@task_app.command("list")
def list_tasks():
    """List all tasks."""
    try:
        with console.status("[bold cyan]Fetching tasks...[/bold cyan]"):
            response = requests.get(f"{config.api_url}/api/tasks", headers=get_headers())
            response.raise_for_status()
            tasks = response.json()
        
        table = Table(title="[bold]NEXUS Tasks[/bold]", box=box.ROUNDED, header_style="bold magenta")
        table.add_column("ID", justify="right", style="dim", width=4)
        table.add_column("Title")
        table.add_column("Project", justify="right", style="cyan")
        table.add_column("Status")
        
        for t in tasks:
            status_icon = "✅ Done" if t.get("is_completed") else "⏳ Pending"
            status_color = "green" if t.get("is_completed") else "yellow"
            table.add_row(str(t["id"]), t["title"], str(t.get("project_id", "-")), f"[{status_color}]{status_icon}[/{status_color}]")
        
        console.print(table)
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error fetching tasks[/bold red]", border_style="red", expand=False))

@task_app.command("add")
def add_task(title: str, project_id: int):
    """Add a new task to a project."""
    try:
        with console.status("[bold cyan]Adding task...[/bold cyan]"):
            payload = {"title": title, "project_id": project_id}
            response = requests.post(f"{config.api_url}/api/tasks", json=payload, headers=get_headers())
            response.raise_for_status()
            t = response.json()
        console.print(Panel(f"Title: [bold]{t['title']}[/bold]\nProject ID: {t.get('project_id')}", title=f"[bold green]Task Added (ID: {t['id']})[/bold green]", border_style="green", expand=False))
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error adding task[/bold red]", border_style="red", expand=False))

# --- NOTES ---
@note_app.command("add")
def add_note(title: str, content: str):
    """Add a quick note."""
    try:
        with console.status("[bold cyan]Saving note...[/bold cyan]"):
            payload = {"title": title, "content": content}
            response = requests.post(f"{config.api_url}/api/notes", json=payload, headers=get_headers())
            response.raise_for_status()
            n = response.json()
        console.print(Panel(f"[dim]{n.get('content', '')}[/dim]", title=f"[bold blue]Note Saved: {n['title']} (ID: {n['id']})[/bold blue]", border_style="blue", expand=False))
    except Exception as e:
        console.print(Panel(str(e), title="[bold red]Error adding note[/bold red]", border_style="red", expand=False))

if __name__ == "__main__":
    app()
