"""Account and sovereign data inspection commands."""

import typer

from ..client import get_client
from ..errors import ExitCode, NexusError
from ..ui import (
    console,
    is_json_mode,
    output_json,
    print_error,
    print_info,
    render_key_value,
    set_json_mode,
    status_spinner,
)

account_app = typer.Typer(help="Inspect sovereign account details and entity metrics")


@account_app.command("overview")
def account_overview(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Display sovereign account identity, Google identity linking, and node metrics."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        with status_spinner("Fetching account overview…"):
            resp = client.get("/api/account/overview")
        ov = resp.json()
        if is_json_mode():
            output_json(ov)
            return

        google_ident = ov.get("google_identity") or {}
        render_key_value(
            {
                "Account ID": ov.get("account_id"),
                "Email": ov.get("email"),
                "Role": ov.get("role", "user").upper(),
                "Active Status": "Active" if ov.get("is_active") else "Suspended",
                "Registered At": ov.get("created_at", "")[:10],
                "Total Devices": ov.get("devices", {}).get("total", 0),
                "Active Devices": ov.get("devices", {}).get("active", 0),
                "Active Sessions": ov.get("sessions", {}).get("active", 0),
                "Google Linked": "Yes" if google_ident else "No",
                "Google Name": google_ident.get("name", "N/A"),
            },
            title="NEXUS ACCOUNT OVERVIEW",
        )
    except NexusError as e:
        print_error(e.message, title="ACCOUNT OVERVIEW FAILED", hint="Run 'nexus auth login' first.")
        raise typer.Exit(e.exit_code)


@account_app.command("data")
def account_data(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Display sovereign entity tallies and storage retention policy."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        with status_spinner("Fetching data summary…"):
            resp = client.get("/api/account/data-summary")
        summary = resp.json()
        if is_json_mode():
            output_json(summary)
            return

        entities = summary.get("supported_entities", {})
        render_key_value(
            {
                "Projects": entities.get("projects", 0),
                "Tasks": entities.get("tasks", 0),
                "Notes": entities.get("notes", 0),
                "Inbox Items": entities.get("inbox_items", 0),
                "Storage Policy": summary.get("sovereign_storage_policy", "Local edge retention"),
                "Cloud Retained Bytes": f"{summary.get('cloud_stored_bytes', 0)} Bytes (Zero Cloud Retention)",
            },
            title="SOVEREIGN DATA SUMMARY",
        )
    except NexusError as e:
        print_error(e.message, title="ACCOUNT DATA FAILED")
        raise typer.Exit(e.exit_code)


@account_app.command("activity")
def account_activity(
    category: str = typer.Option("all", help="Activity category filter: all | auth | device | session"),
    limit: int = typer.Option(20, help="Maximum events to return"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Show audit event stream for the current account."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        with status_spinner("Fetching activity…"):
            resp = client.get(f"/api/account/activity?category={category}&limit={limit}")
        page = resp.json()
        if is_json_mode():
            output_json(page)
            return

        events = page.get("items", [])
        if not events:
            print_info("No activity recorded for this filter.", title="ACCOUNT ACTIVITY")
            return

        console.print(f"[bold cyan]NEXUS Activity Timeline ({len(events)} events)[/bold cyan]")
        for ev in events:
            time_str = ev.get("created_at", "")[:19].replace("T", " ")
            action = ev.get("action", "")
            detail = ev.get("detail", "")
            console.print(f"  [dim]{time_str}[/dim]  [bold yellow]{action.ljust(22)}[/bold yellow]  {detail}")
    except NexusError as e:
        print_error(e.message, title="ACTIVITY FAILED")
        raise typer.Exit(e.exit_code)
