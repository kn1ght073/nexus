"""Node registration, coordination, and relay bridge commands."""

import platform as _platform
from typing import Optional

import typer

from ..client import get_client
from ..config import load_config, save_config
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

nodes_app = typer.Typer(help="Manage edge nodes, pairing codes, and relay bridges")


@nodes_app.command("list")
def list_nodes(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List all registered edge nodes and live heartbeats."""
    if json_output:
        set_json_mode(True)
    cfg = load_config()
    base_url = cfg.control_plane_url or cfg.api_url
    client = get_client(base_url=base_url)

    try:
        with status_spinner("Fetching registered nodes…"):
            resp = client.get("/api/nodes")
        nodes = resp.json()
        if is_json_mode():
            output_json(nodes)
            return

        if not nodes:
            print_info("No nodes registered yet. Claim one via 'nexus nodes claim'.", title="REGISTERED NODES")
            return

        table = create_table(
            "NEXUS Nodes",
            [
                {"name": "ID", "justify": "right", "width": 4},
                {"name": "Name", "style": "bold cyan"},
                {"name": "Platform"},
                {"name": "Active", "justify": "center"},
                {"name": "Liveness", "justify": "center"},
                {"name": "Last Seen"},
            ],
        )
        for n in nodes:
            active = "[bold green]★ PRIMARY[/bold green]" if n.get("is_active") else "[dim]STANDBY[/dim]"
            liveness = "[bold green]● ONLINE[/bold green]" if n.get("is_online") else "[dim]○ STALE[/dim]"
            last_seen = n.get("last_seen", "")[:19].replace("T", " ")
            table.add_row(str(n["id"]), n["name"], n.get("platform", "-"), active, liveness, last_seen)

        console.print(table)
    except NexusError as e:
        print_error(e.message, title="NODES LIST FAILED")
        raise typer.Exit(e.exit_code)


@nodes_app.command("resolve")
def resolve_node(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Resolve which node is currently elected as active main server."""
    if json_output:
        set_json_mode(True)
    cfg = load_config()
    base_url = cfg.control_plane_url or cfg.api_url
    client = get_client(base_url=base_url)

    try:
        with status_spinner("Resolving active node…"):
            resp = client.get("/api/nodes/active")
        node = resp.json()
        if is_json_mode():
            output_json(node)
            return

        if not node:
            print_info("No active edge node is currently online.", title="ACTIVE NODE")
            return

        render_key_value(
            {
                "Node ID": f"#{node['id']}",
                "Name": node["name"],
                "Platform": node.get("platform", "-"),
                "Endpoint": node.get("endpoint") or "Direct link offline — using relay",
                "Last Heartbeat": node.get("last_seen", "")[:19].replace("T", " "),
            },
            title="ACTIVE EDGE NODE",
        )
    except NexusError as e:
        print_error(e.message, title="RESOLVE FAILED")
        raise typer.Exit(e.exit_code)


@nodes_app.command("claim")
def claim_node(
    name: str = typer.Option("My Node", help="Display name for this edge node"),
    platform: Optional[str] = typer.Option(None, help="Operating system (macos | windows | linux)"),
    endpoint: Optional[str] = typer.Option(None, help="Direct endpoint URL/host:port or leave blank for relay"),
    watch: bool = typer.Option(False, "--watch", help="Keep running in foreground and send heartbeats every 30s"),
    bridge: bool = typer.Option(True, "--bridge/--no-bridge", help="Run the secure outbound relay bridge"),
):
    """Claim this host machine as the authoritative NEXUS edge node."""
    cfg = load_config()
    base_url = cfg.control_plane_url or cfg.api_url
    client = get_client(base_url=base_url)

    if not platform:
        sys_name = _platform.system()
        platform = {"Darwin": "macos", "Windows": "windows"}.get(sys_name, "linux")

    try:
        with status_spinner(f"Claiming node '{name}' on {base_url}…"):
            resp = client.post(
                "/api/nodes/claim",
                json={"name": name, "platform": platform, "endpoint": endpoint},
            )
        node = resp.json()

        cfg.node_id = node["id"]
        cfg.node_api_key = node["api_key"]
        save_config(cfg)

        print_success(
            f"Node [bold cyan]{node['name']}[/bold cyan] (#{node['id']}) claimed successfully.\n"
            f"API Key saved securely in configuration.",
            title="NODE CLAIMED",
        )

        if watch:
            import time
            console.print("[dim]Heartbeating every 30s — Press Ctrl-C to terminate.[/dim]")
            while True:
                try:
                    client.post(f"/api/nodes/{node['id']}/heartbeat")
                    console.print("[dim]♥ heartbeat acknowledged[/dim]")
                except Exception as ex:
                    console.print(f"[red]heartbeat failed: {ex}[/red]")
                time.sleep(30)
    except NexusError as e:
        print_error(e.message, title="NODE CLAIM FAILED")
        raise typer.Exit(e.exit_code)
    except KeyboardInterrupt:
        console.print("\n[dim]Node monitor stopped.[/dim]")


@nodes_app.command("pair")
def mint_pairing_code():
    """Mint a temporary 6-digit numeric pairing code for edge onboarding."""
    cfg = load_config()
    base_url = cfg.control_plane_url or cfg.api_url
    client = get_client(base_url=base_url)

    try:
        with status_spinner("Generating edge pairing code…"):
            resp = client.post("/api/nodes/pair")
        data = resp.json()
        if is_json_mode():
            output_json(data)
            return

        render_key_value(
            {
                "Pairing Code": f"[bold yellow]{data['code']}[/bold yellow]",
                "Expires In": f"{data.get('expires_in', 600) // 60} minutes",
            },
            title="EDGE PAIRING CODE",
        )
        console.print("[dim]Enter this code on your client to pair with this node over the secure relay.[/dim]")
    except NexusError as e:
        print_error(e.message, title="PAIRING CODE FAILED")
        raise typer.Exit(e.exit_code)
