"""Note capture, management, and listing commands."""

from typing import Optional

import typer
from rich.panel import Panel
from rich.prompt import Prompt

from ..client import get_client
from ..errors import NexusError
from ..local_store import create_local_note, delete_local_note, list_local_notes
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

notes_app = typer.Typer(help="Manage sovereign notes, documentation, and quick thoughts")


@notes_app.command("list")
def list_notes(
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Filter by project ID"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List all saved notes."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    notes = []
    source = "Remote Node"
    try:
        with status_spinner("Fetching notes…"):
            params = {}
            if project_id is not None:
                params["project_id"] = project_id
            resp = client.get("/api/notes", params=params)
        notes = resp.json()
    except Exception:
        notes = list_local_notes()
        if project_id is not None:
            notes = [n for n in notes if n.get("project_id") == project_id]
        source = "Local Sovereign Store"

    if is_json_mode():
        output_json(notes)
        return

    if not notes:
        print_info("No notes found. Capture one via 'nexus notes add <title> <content>'.", title="NOTES")
        return

    table = create_table(
        f"NEXUS Sovereign Notes ({source})",
        [
            {"name": "ID", "justify": "right", "width": 4},
            {"name": "Title", "style": "bold cyan"},
            {"name": "Content Preview"},
            {"name": "Project", "style": "magenta"},
            {"name": "Updated At"},
        ],
    )
    for n in notes:
        content = (n.get("content") or "").replace("\n", " ")
        preview = content[:50] + ("…" if len(content) > 50 else "")
        proj_str = f"#{n['project_id']}" if n.get("project_id") else "—"
        table.add_row(
            str(n["id"]),
            n["title"],
            preview,
            proj_str,
            n.get("updated_at", "")[:19].replace("T", " "),
        )

    console.print(table)


@notes_app.command("add")
@notes_app.command("create")
def add_note(
    title: Optional[str] = typer.Argument(None, help="Title of the note (prompts interactively if omitted)"),
    content: Optional[str] = typer.Argument(None, help="Body content of the note (prompts interactively if omitted)"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Optional project ID"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags (e.g. 'research,kernel')"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Add a quick sovereign note (interactively prompts if arguments are omitted)."""
    if json_output:
        set_json_mode(True)

    if not title:
        title = Prompt.ask("[bold cyan]Note Title[/bold cyan]")
        while not title.strip():
            title = Prompt.ask("[bold red]Note title cannot be empty. Please enter title[/bold red]")

    if not content:
        content = Prompt.ask("[bold cyan]Note Content (markdown/text)[/bold cyan]")
        while not content.strip():
            content = Prompt.ask("[bold red]Note content cannot be empty. Please enter content[/bold red]")

    client = get_client()
    n = None
    source = "Remote Node"
    body = {"title": title.strip(), "content": content.strip()}
    if project_id is not None:
        body["project_id"] = project_id
    if tags:
        body["tags"] = tags.strip()

    try:
        with status_spinner("Saving note…"):
            resp = client.post("/api/notes", json=body)
        n = resp.json()
    except Exception:
        n = create_local_note(title=title.strip(), content=content.strip(), tags=tags, project_id=project_id)
        source = "Local Sovereign Store"

    if is_json_mode():
        output_json(n)
        return
    print_success(f"Note #{n['id']} '{n['title']}' saved in {source}.", title="NOTE SAVED")


@notes_app.command("show")
def show_note(
    note_id: int = typer.Argument(..., help="ID of the note to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Display full content and metadata for a specific note."""
    if json_output:
        set_json_mode(True)

    client = get_client()
    note = None
    source = "Remote Node"
    try:
        with status_spinner(f"Loading note #{note_id}…"):
            resp = client.get(f"/api/notes/{note_id}")
        note = resp.json()
    except Exception:
        all_local = list_local_notes()
        note = next((n for n in all_local if n["id"] == note_id), None)
        source = "Local Sovereign Store"

    if not note:
        print_error(f"Note #{note_id} not found in remote or local store.", title="NOT FOUND")
        raise typer.Exit(1)

    if is_json_mode():
        output_json(note)
        return

    meta = (
        f"[bold]ID:[/bold] #{note['id']}  |  "
        f"[bold]Project:[/bold] {note.get('project_id') or 'None'}  |  "
        f"[bold]Tags:[/bold] {note.get('tags') or 'None'}  |  "
        f"[bold]Updated:[/bold] {note.get('updated_at', '')[:19].replace('T', ' ')}"
    )
    panel = Panel(
        f"{meta}\n\n[dim]──────────────────────────────────────────────[/dim]\n\n{note.get('content', '')}",
        title=f"📝 {note['title']} ({source})",
        border_style="cyan",
        expand=False,
    )
    console.print(panel)


@notes_app.command("delete")
@notes_app.command("rm")
def delete_note(
    note_id: int = typer.Argument(..., help="ID of the note to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete without confirmation prompt"),
):
    """Delete a sovereign note."""
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete note #{note_id}?")
        if not confirm:
            print_info("Deletion cancelled.")
            return

    client = get_client()
    deleted = False
    try:
        with status_spinner(f"Deleting note #{note_id}…"):
            client.delete(f"/api/notes/{note_id}")
        deleted = True
    except Exception:
        pass

    local_del = delete_local_note(note_id)
    if deleted or local_del:
        print_success(f"Note #{note_id} deleted successfully.", title="NOTE DELETED")
    else:
        print_error(f"Could not delete note #{note_id}. It may not exist.", title="DELETE FAILED")
        raise typer.Exit(1)
