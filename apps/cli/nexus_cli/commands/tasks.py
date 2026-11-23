"""Task management and completion commands."""

from typing import Optional

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

tasks_app = typer.Typer(help="Manage sovereign tasks and daily objectives")


def _render_tasks_table(tasks: list) -> None:
    if not tasks:
        print_info("No tasks found.", title="TASKS")
        return

    table = create_table(
        "NEXUS Tasks",
        [
            {"name": "ID", "justify": "right", "width": 4},
            {"name": "Title", "style": "bold white"},
            {"name": "Project", "justify": "right", "width": 8},
            {"name": "Status", "justify": "center"},
            {"name": "Revision", "justify": "right", "width": 4},
        ],
    )
    for t in tasks:
        status = t.get("status", "pending")
        icon = {"completed": "✅ DONE", "in_progress": "🔄 ACTIVE"}.get(status, "⏳ PENDING")
        color = {"completed": "green", "in_progress": "blue"}.get(status, "yellow")
        proj = f"#{t['project_id']}" if t.get("project_id") else "-"
        table.add_row(str(t["id"]), t["title"], proj, f"[{color}]{icon}[/{color}]", str(t.get("revision", 1)))
    console.print(table)


@tasks_app.command("list")
def list_tasks(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List all active tasks."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        with status_spinner("Fetching tasks…"):
            resp = client.get("/api/tasks")
        tasks = resp.json()
        if is_json_mode():
            output_json(tasks)
            return
        _render_tasks_table(tasks)
    except NexusError as e:
        print_error(e.message, title="TASKS FAILED")
        raise typer.Exit(e.exit_code)


@tasks_app.command("today")
def today_tasks(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List tasks assigned or created today."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        with status_spinner("Fetching today's tasks…"):
            resp = client.get("/api/tasks/today")
        tasks = resp.json()
        if is_json_mode():
            output_json(tasks)
            return
        _render_tasks_table(tasks)
    except NexusError as e:
        print_error(e.message, title="TODAY TASKS FAILED")
        raise typer.Exit(e.exit_code)


@tasks_app.command("add")
def add_task(
    title: str = typer.Argument(..., help="Task title"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Optional project ID"),
):
    """Add a new task."""
    client = get_client()
    payload = {"title": title}
    if project_id:
        payload["project_id"] = project_id
    try:
        with status_spinner("Adding task…"):
            resp = client.post("/api/tasks", json=payload)
        t = resp.json()
        if is_json_mode():
            output_json(t)
            return
        print_success(f"Task #{t['id']} created: '{t['title']}'.", title="TASK ADDED")
    except NexusError as e:
        print_error(e.message, title="ADD TASK FAILED")
        raise typer.Exit(e.exit_code)


@tasks_app.command("done")
def done_task(task_id: int = typer.Argument(..., help="ID of task to complete")):
    """Mark a task as completed."""
    client = get_client()
    try:
        with status_spinner(f"Completing task #{task_id}…"):
            resp = client.put(f"/api/tasks/{task_id}", json={"status": "completed"})
        t = resp.json()
        if is_json_mode():
            output_json(t)
            return
        print_success(f"Task #{t['id']} marked as completed.", title="TASK COMPLETED")
    except NexusError as e:
        print_error(e.message, title="COMPLETE TASK FAILED")
        raise typer.Exit(e.exit_code)
