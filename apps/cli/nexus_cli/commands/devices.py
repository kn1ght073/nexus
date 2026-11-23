"""Device management and token minting commands."""

from typing import Optional

import typer

from ..client import get_client
from ..errors import ExitCode, NexusError
from ..ui import (
    console,
    create_table,
    is_json_mode,
    output_json,
    print_error,
    print_info,
    print_success,
    render_key_value,
    set_json_mode,
    status_spinner,
)

devices_app = typer.Typer(help="Manage registered hardware devices and device tokens")


@devices_app.command("list")
def list_devices(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List all registered hardware devices."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        with status_spinner("Fetching registered devices…"):
            resp = client.get("/api/devices")
        devs = resp.json()
        if is_json_mode():
            output_json(devs)
            return

        if not devs:
            print_info("No devices registered to this account.", title="REGISTERED DEVICES")
            return

        table = create_table(
            "NEXUS Devices",
            [
                {"name": "ID", "justify": "right", "width": 4},
                {"name": "Name", "style": "bold cyan"},
                {"name": "Platform"},
                {"name": "Status", "justify": "center"},
                {"name": "Last Active"},
                {"name": "Capabilities"},
            ],
        )
        for d in devs:
            online = "[bold green]● online[/bold green]" if d.get("is_online") else "[dim]○ offline[/dim]"
            caps = ", ".join(d.get("capabilities", [])) or "-"
            last_seen = d.get("last_seen", "")[:19].replace("T", " ")
            table.add_row(str(d["id"]), d["name"], d.get("platform", "-"), online, last_seen, caps)

        console.print(table)
    except NexusError as e:
        print_error(e.message, title="DEVICES FAILED", hint="Run 'nexus auth login' first.")
        raise typer.Exit(e.exit_code)


@devices_app.command("inspect")
def inspect_device(
    device_id: int = typer.Argument(..., help="Device ID to inspect"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Inspect metadata and capabilities for a specific device."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        resp = client.get("/api/devices")
        devs = resp.json()
        target = next((d for d in devs if d["id"] == device_id), None)
        if not target:
            print_error(f"Device #{device_id} not found on this account.", title="NOT FOUND")
            raise typer.Exit(ExitCode.NOT_FOUND)

        if is_json_mode():
            output_json(target)
            return

        render_key_value(
            {
                "Device ID": f"#{target['id']}",
                "Name": target["name"],
                "Platform": target.get("platform", "-"),
                "Online": "Yes" if target.get("is_online") else "No",
                "Last Seen": target.get("last_seen", "")[:19].replace("T", " "),
                "Capabilities": ", ".join(target.get("capabilities", [])) or "None",
            },
            title=f"DEVICE #{target['id']}",
        )
    except NexusError as e:
        print_error(e.message, title="INSPECT FAILED")
        raise typer.Exit(e.exit_code)


@devices_app.command("revoke")
def revoke_device(
    device_id: int = typer.Argument(..., help="Device ID to revoke access"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Revoke a device's authorization and unlink it permanently."""
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to permanently revoke device #{device_id}?")
        if not confirm:
            print_info("Device revocation cancelled.", title="ABORTED")
            return

    client = get_client()
    try:
        with status_spinner(f"Revoking device #{device_id}…"):
            client.delete(f"/api/devices/{device_id}")
        print_success(f"Device #{device_id} has been revoked and disconnected.", title="DEVICE REVOKED")
    except NexusError as e:
        print_error(e.message, title="REVOCATION FAILED")
        raise typer.Exit(e.exit_code)


@devices_app.command("token")
def issue_device_token(
    platform_name: str = typer.Option("android", "--platform", "-p", help="Target platform (android | desktop | web)"),
    expires_minutes: int = typer.Option(10, "--expires", "-e", help="Token lifetime in minutes"),
):
    """Mint a single-use onboarding token for new clients (phone, laptop)."""
    client = get_client()
    try:
        with status_spinner("Generating device onboarding token…"):
            resp = client.post(
                "/api/devices/token",
                json={"platform": platform_name, "expires_in_minutes": expires_minutes},
            )
        data = resp.json()
        if is_json_mode():
            output_json(data)
            return

        token = data.get("token")
        render_key_value(
            {
                "Pairing Token": f"[bold green]{token}[/bold green]",
                "Target Platform": platform_name,
                "Lifetime": f"{expires_minutes} minutes",
                "Expires At": data.get("expires_at", "")[:19].replace("T", " "),
            },
            title="DEVICE ONBOARDING TOKEN",
        )
        console.print("[dim]Use this token on your mobile or desktop client to authenticate automatically.[/dim]")
    except NexusError as e:
        print_error(e.message, title="TOKEN MINTING FAILED")
        raise typer.Exit(e.exit_code)
