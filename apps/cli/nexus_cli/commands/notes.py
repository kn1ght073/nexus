"""Note capture and listing commands."""

from typing import Optional

import typer

from ..client import get_client
from ..errors import NexusError
from ..local_store import create_local_note, list_local_notes
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

notes_app = typer.Typer(help="Manage sovereign notes and quick thoughts")


@notes_app.command("list")
def list_notes(
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
            resp = client.get("/api/notes")
        notes = resp.json()
    except Exception:
        notes = list_local_notes()
        source = "Local Sovereign Store"

    if is_json_mode():
        output_json(notes)
        return

    if not notes:
        print_info("No notes found. Capture one via 'nexus note add <title> <content>'.", title="NOTES")
        return

    table = create_table(
        f"NEXUS Notes ({source})",
        [
            {"name": "ID", "justify": "right", "width": 4},
            {"name": "Title", "style": "bold cyan"},
            {"name": "Content Preview"},
            {"name": "Updated At"},
        ],
    )
    for n in notes:
        content = (n.get("content") or "").replace("\n", " ")
        preview = content[:50] + ("…" if len(content) > 50 else "")
        table.add_row(str(n["id"]), n["title"], preview, n.get("updated_at", "")[:19].replace("T", " "))

    console.print(table)


@notes_app.command("add")
def add_note(
    title: str = typer.Argument(..., help="Title of the note"),
    content: str = typer.Argument(..., help="Body content of the note"),
    project_id: Optional[int] = typer.Option(None, "--project", "-p", help="Optional project ID"),
):
    """Add a quick sovereign note."""
    client = get_client()
    n = None
    source = "Remote Node"
    body = {"title": title, "content": content}
    if project_id is not None:
        body["project_id"] = project_id
    try:
        with status_spinner("Saving note…"):
            resp = client.post("/api/notes", json=body)
        n = resp.json()
    except Exception:
        n = create_local_note(title=title, content=content, project_id=project_id)
        source = "Local Sovereign Store"

    if is_json_mode():
        output_json(n)
        return
    print_success(f"Note #{n['id']} '{n['title']}' saved in {source}.", title="NOTE SAVED")
