"""Local filesystem browsing and jailed text search commands."""

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
    render_key_value,
    set_json_mode,
    status_spinner,
)

files_app = typer.Typer(help="Browse and search files inside the server's storage roots")


@files_app.command("list")
def list_files(
    path: Optional[str] = typer.Argument(None, help="Directory path to browse"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List files in the jailed storage roots."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    params = {"path": path} if path else {}
    try:
        with status_spinner("Browsing storage roots…"):
            resp = client.get("/api/files/browse", params=params)
        files = resp.json()
        if is_json_mode():
            output_json(files)
            return

        table = create_table(
            f"Files: {path or 'Default Root'}",
            [
                {"name": "Type", "width": 6, "justify": "center"},
                {"name": "Name", "style": "bold white"},
                {"name": "Size", "justify": "right"},
                {"name": "Path", "style": "dim"},
            ],
        )
        for f in files:
            icon = "📁 DIR" if f.get("is_dir") else "📄 FILE"
            size = f"{f['size']:,} B" if not f.get("is_dir") else "-"
            table.add_row(icon, f["name"], size, f["path"])

        console.print(table)
    except NexusError as e:
        print_error(e.message, title="FILE BROWSE FAILED")
        raise typer.Exit(e.exit_code)


@files_app.command("roots")
def show_roots(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List the server's configured storage roots (path jail boundaries)."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        with status_spinner("Fetching storage roots…"):
            resp = client.get("/api/files/roots")
        roots = resp.json()
        if is_json_mode():
            output_json(roots)
            return

        render_key_value(
            {f"Root #{i+1}": r for i, r in enumerate(roots)},
            title="CONFIGURED STORAGE ROOTS",
        )
    except NexusError as e:
        print_error(e.message, title="STORAGE ROOTS FAILED")
        raise typer.Exit(e.exit_code)


@files_app.command("search")
def search_files(
    query: str = typer.Argument(..., help="Search keyword or phrase"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Directory within storage roots"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Search for text within files inside the storage roots."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    params = {"query": query}
    if path:
        params["path"] = path

    try:
        with status_spinner(f"Searching for '{query}'…"):
            resp = client.get("/api/files/search", params=params)
        results = resp.json()
        if is_json_mode():
            output_json(results)
            return

        if not results:
            print_info(f"No matches found for '{query}'.", title="SEARCH RESULTS")
            return

        table = create_table(
            f"Search Results for '{query}'",
            [
                {"name": "File", "style": "bold white"},
                {"name": "Matching Context"},
            ],
        )
        for r in results:
            table.add_row(r.get("path", "-"), r.get("match_context", "-"))

        console.print(table)
    except NexusError as e:
        print_error(e.message, title="FILE SEARCH FAILED")
        raise typer.Exit(e.exit_code)
