"""Incremental synchronization pull and push commands."""

from typing import Optional

import typer

from ..client import get_client
from ..errors import NexusError
from ..local_store import sync_local_store_with_host_db
from ..ui import (
    console,
    is_json_mode,
    output_json,
    print_error,
    print_success,
    render_key_value,
    set_json_mode,
    status_spinner,
)

sync_app = typer.Typer(help="Synchronize sovereign data across devices")


@sync_app.command("pull")
def sync_pull(
    since: Optional[str] = typer.Option(None, "--since", "-s", help="ISO timestamp cursor for incremental changes"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Pull incremental entity changes (projects, tasks, notes) since cursor."""
    sync_local_store_with_host_db()
    if json_output:
        set_json_mode(True)
    client = get_client()
    payload = {"since": since} if since else {}

    try:
        with status_spinner("Pulling sync delta from node…"):
            resp = client.post("/api/sync/pull", json=payload)
        body = resp.json()
        if is_json_mode():
            output_json(body)
            return

        changes = body.get("changes", {})
        counts = {k: len(v) for k, v in changes.items()}
        total = sum(counts.values())

        print_success(
            f"Synced {total} change(s) from node.",
            title="SYNC PULL COMPLETE",
            details=f"Server Timestamp: {body.get('server_time')}",
        )
        render_key_value(
            {
                "Projects Updated": counts.get("projects", 0),
                "Tasks Updated": counts.get("tasks", 0),
                "Notes Updated": counts.get("notes", 0),
            },
            title="DELTA BREAKDOWN",
        )
    except NexusError as e:
        print_error(e.message, title="SYNC PULL FAILED")
        raise typer.Exit(e.exit_code)
