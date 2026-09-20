import typer
import requests
from rich.console import Console
from rich.table import Table
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
    console.print(f"[green]Successfully initialized NEXUS CLI![/green] API URL set to: {config.api_url}")

@app.command()
def status():
    """Check the connection to the NEXUS core node."""
    try:
        response = requests.get(f"{config.api_url}/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        console.print(f"[green]SUCCESS:[/green] Connected to {data.get('service', 'NEXUS Node')}")
    except requests.exceptions.RequestException as e:
        console.print(f"[red]ERROR:[/red] Could not connect to NEXUS at {config.api_url}. Is the server running?")

# --- PROJECTS ---
@project_app.command("list")
def list_projects():
    """List all projects."""
    try:
        response = requests.get(f"{config.api_url}/api/projects", headers=get_headers())
        response.raise_for_status()
        projects = response.json()
        
        table = Table("ID", "Title", "Status")
        for p in projects:
            table.add_row(str(p["id"]), p["title"], p.get("status", "unknown"))
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error fetching projects: {e}[/red]")

@project_app.command("create")
def create_project(title: str, description: str = ""):
    """Create a new project."""
    try:
        payload = {"title": title, "description": description}
        response = requests.post(f"{config.api_url}/api/projects", json=payload, headers=get_headers())
        response.raise_for_status()
        p = response.json()
        console.print(f"[green]Project created![/green] ID: {p['id']}, Title: {p['title']}")
    except Exception as e:
        console.print(f"[red]Error creating project: {e}[/red]")

# --- TASKS ---
@task_app.command("list")
def list_tasks():
    """List all tasks."""
    try:
        response = requests.get(f"{config.api_url}/api/tasks", headers=get_headers())
        response.raise_for_status()
        tasks = response.json()
        
        table = Table("ID", "Title", "Project ID", "Status")
        for t in tasks:
            table.add_row(str(t["id"]), t["title"], str(t.get("project_id", "-")), str(t.get("is_completed", False)))
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error fetching tasks: {e}[/red]")

@task_app.command("add")
def add_task(title: str, project_id: int):
    """Add a new task to a project."""
    try:
        payload = {"title": title, "project_id": project_id}
        response = requests.post(f"{config.api_url}/api/tasks", json=payload, headers=get_headers())
        response.raise_for_status()
        t = response.json()
        console.print(f"[green]Task added![/green] ID: {t['id']}, Title: {t['title']}")
    except Exception as e:
        console.print(f"[red]Error adding task: {e}[/red]")

# --- NOTES ---
@note_app.command("add")
def add_note(title: str, content: str):
    """Add a quick note."""
    try:
        payload = {"title": title, "content": content}
        response = requests.post(f"{config.api_url}/api/notes", json=payload, headers=get_headers())
        response.raise_for_status()
        n = response.json()
        console.print(f"[green]Note saved![/green] ID: {n['id']}, Title: {n['title']}")
    except Exception as e:
        console.print(f"[red]Error adding note: {e}[/red]")

if __name__ == "__main__":
    app()
