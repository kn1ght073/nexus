"""Note capture and listing commands."""

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

notes_app = typer.Typer(help="Manage sovereign notes and quick thoughts")


@notes_app.command("list")
def list_notes(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List all saved notes."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        with status_spinner("Fetching notes…"):
            resp = client.get("/api/notes")
        notes = resp.json()
        if is_json_mode():
            output_json(notes)
            return

        if not notes:
            print_info("No notes found. Capture one via 'nexus note add <title> <content>'.", title="NOTES")
            return

        table = create_table(
            "NEXUS Notes",
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
    except NexusError as e:
        print_error(e.message, title="NOTES FAILED")
        raise typer.Exit(e.exit_code)


@notes_app.command("add")
def add_note(
    title: str = typer.Argument(..., help="Title of the note"),
    content: str = typer.Argument(..., help="Body content of the note"),
):
    """Add a quick sovereign note."""
    client = get_client()
    try:
        with status_spinner("Saving note…"):
            resp = client.post("/api/notes", json={"title": title, "content": content})
        n = resp.json()
        if is_json_mode():
            output_json(n)
            return
        print_success(f"Note #{n['id']} '{n['title']}' saved.", title="NOTE SAVED")
    except NexusError as e:
        print_error(e.message, title="NOTE SAVE FAILED")
        raise typer.Exit(e.exit_code)
