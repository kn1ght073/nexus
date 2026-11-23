"""Project management commands."""

import typer

from ..client import get_client
from ..errors import NexusError
from ..ui import (
    console,
    create_table,
    is_json_mode,
    output_json,
    print_error,
    print_info,
    print_success,
    set_json_mode,
    status_spinner,
)

projects_app = typer.Typer(help="Manage sovereign projects")


@projects_app.command("list")
def list_projects(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List all active projects."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        with status_spinner("Fetching projects…"):
            resp = client.get("/api/projects")
        projects = resp.json()
        if is_json_mode():
            output_json(projects)
            return

        if not projects:
            print_info("No projects found. Create one with 'nexus project create <title>'.", title="PROJECTS")
            return

        table = create_table(
            "NEXUS Projects",
            [
                {"name": "ID", "justify": "right", "width": 4},
                {"name": "Title", "style": "bold cyan"},
                {"name": "Status"},
                {"name": "Revision", "justify": "right"},
                {"name": "Updated At"},
            ],
        )
        for p in projects:
            st = p.get("status", "pending")
            st_color = "green" if st == "completed" else "yellow"
            table.add_row(
                str(p["id"]),
                p["title"],
                f"[{st_color}]{st.upper()}[/{st_color}]",
                str(p.get("revision", 1)),
                p.get("updated_at", "")[:19].replace("T", " "),
            )

        console.print(table)
    except NexusError as e:
        print_error(e.message, title="PROJECTS FAILED")
        raise typer.Exit(e.exit_code)


@projects_app.command("create")
def create_project(
    title: str = typer.Argument(..., help="Title of the project"),
    description: str = typer.Option("", "--desc", "-d", help="Optional project description"),
):
    """Create a new sovereign project."""
    client = get_client()
    try:
        with status_spinner("Creating project…"):
            resp = client.post("/api/projects", json={"title": title, "description": description})
        p = resp.json()
        if is_json_mode():
            output_json(p)
            return
        print_success(f"Project '{p['title']}' created successfully (ID #{p['id']}).", title="PROJECT CREATED")
    except NexusError as e:
        print_error(e.message, title="PROJECT CREATION FAILED")
        raise typer.Exit(e.exit_code)
