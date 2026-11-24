"""Node Management Center Widget for NEXUS Control Center."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DataTable, Input, Label, Static

from ...client import get_client
from ...config import load_config
from .context import ContextPanel


class NodesView(Static):
    """Edge Node Explorer view showing claimed compute nodes, heartbeats, and pairing controls."""

    class NodeAction(Message):
        def __init__(self, action_id: str, node: Optional[Dict[str, Any]] = None) -> None:
            self.action_id = action_id
            self.node = node or {}
            super().__init__()

    _nodes_cache: List[Dict[str, Any]] = []
    _nodes_by_id: Dict[str, Dict[str, Any]] = {}
    selected_node: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="nodes-container"):
            with Horizontal(classes="view-header-bar"):
                yield Label("🖥️ EDGE NODE MANAGEMENT CENTER", classes="view-title")
                with Horizontal(classes="header-actions"):
                    yield Input(placeholder="Filter nodes... (name, platform)", id="node-filter-input")
                    yield Button("🔄 Refresh", id="btn-nodes-refresh", classes="btn-sm")
                    yield Button("🔑 Claim Node", id="btn-node-claim", variant="primary", classes="btn-sm")
                    yield Button("🔗 Pair Code", id="btn-node-pair-code", classes="btn-sm")

            with Horizontal(id="nodes-split-body"):
                # Left pane: Nodes Table
                with Vertical(id="nodes-table-container"):
                    table = DataTable(id="nodes-table", cursor_type="row")
                    table.zebra_stripes = True
                    yield table

                # Right pane: Node Details
                with Vertical(id="node-details-card", classes="details-box"):
                    yield Label("NODE TELEMETRY & HEALTH", classes="box-title")
                    yield Static("Select an edge node from the table to inspect details.", id="node-details-static")
                    with Horizontal(id="node-action-buttons"):
                        yield Button("Check Liveness", id="btn-node-liveness", classes="btn-sm")
                        yield Button("Revoke Node", id="btn-node-revoke", variant="error", classes="btn-sm")

    def on_mount(self) -> None:
        table = self.query_one("#nodes-table", DataTable)
        table.add_columns("ID", "Name", "Platform", "Active", "Liveness", "Last Seen")
        self.refresh_nodes()

    def refresh_nodes(self, filter_q: str = "") -> None:
        self.run_worker(lambda: self._fetch_nodes(filter_q), thread=True)

    def _fetch_nodes(self, filter_q: str) -> None:
        client = get_client()
        nodes = []
        try:
            r = client.get("/api/nodes", timeout=4)
            if r.status_code == 200:
                nodes = r.json()
        except Exception:
            pass

        self.app.call_from_thread(self._render_nodes_table, nodes, filter_q)

    def _render_nodes_table(self, nodes: List[Dict[str, Any]], filter_q: str) -> None:
        if not self.is_mounted:
            return
        self._nodes_cache = nodes
        self._nodes_by_id.clear()

        try:
            table = self.query_one("#nodes-table", DataTable)
        except Exception:
            return
        table.clear()

        q = filter_q.strip().lower()
        first_row_key = None
        cfg = load_config()

        for n in nodes:
            name = n.get("name", "Unknown Node")
            plat = n.get("platform", "-")
            if q and (q not in name.lower() and q not in plat.lower()):
                continue

            node_id = str(n.get("id"))
            self._nodes_by_id[node_id] = n
            if first_row_key is None:
                first_row_key = node_id

            is_mine = (n.get("id") == cfg.node_id)
            name_display = f"{name} (This Machine)" if is_mine else name

            active_badge = "[bold green]● Active[/bold green]" if n.get("is_active") else "[dim]○ Inactive[/dim]"
            liveness_badge = "[bold green]LIVE[/bold green]" if n.get("is_live", True) else "[bold red]DEAD[/bold red]"
            last_seen = (n.get("last_seen") or "")[:19].replace("T", " ")

            table.add_row(
                node_id,
                f"[bold cyan]{name_display}[/bold cyan]",
                plat,
                active_badge,
                liveness_badge,
                last_seen or "-",
                key=node_id,
            )

        if first_row_key and first_row_key in self._nodes_by_id:
            self._display_node(self._nodes_by_id[first_row_key])

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "node-filter-input":
            self.refresh_nodes(filter_q=event.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value in self._nodes_by_id:
            node = self._nodes_by_id[event.row_key.value]
            self._display_node(node)

    def _display_node(self, node: Dict[str, Any]) -> None:
        self.selected_node = node
        cfg = load_config()
        is_mine = (node.get("id") == cfg.node_id)
        last_seen = (node.get("last_seen") or "")[:19].replace("T", " ") or "N/A"
        services = node.get("services") or {}
        srv_str = ", ".join(f"{k}:{v}" for k, v in services.items()) if services else "None reported"

        lines = [
            f"[bold cyan]{node.get('name', 'Edge Node')}[/bold cyan] {'[green](Current Node)[/green]' if is_mine else ''}",
            f"[dim]Node ID #{node.get('id')}[/dim]",
            "",
            f"[bold]Platform:[/bold] {node.get('platform', '-')}",
            f"[bold]Active Status:[/bold] {'[green]Active[/green]' if node.get('is_active') else '[dim]Inactive[/dim]'}",
            f"[bold]Heartbeat:[/bold] {'[green]● Responding[/green]' if node.get('is_live', True) else '[red]❌ Unreachable[/red]'}",
            f"[bold]Last Seen:[/bold] {last_seen}",
            f"[bold]Local Services:[/bold] {srv_str}",
            f"[bold]Coordination:[/bold] Secure Inbound Relay WebSocket",
            "",
            "[dim]Press Claim to provision new hardware or Generate Code to attach devices.[/dim]",
        ]

        try:
            self.query_one("#node-details-static", Static).update("\n".join(lines))
        except Exception:
            pass

        # Update global ContextPanel
        try:
            ctx = self.app.query_one(ContextPanel)
            ctx.update_resource(
                title=f"Node: {node.get('name')}",
                subtitle=f"Node #{node.get('id')} — {node.get('platform', 'Compute Node')}",
                properties={
                    "Active": "Active" if node.get("is_active") else "Inactive",
                    "Heartbeat": "Responding" if node.get("is_live", True) else "Offline",
                    "Last Seen": last_seen,
                    "Platform": node.get("platform", "-"),
                    "Role": "Primary Node" if is_mine else "Secondary Node",
                },
                action_label="Generate Pairing Code",
                action_id="nodes.pairing_code",
                action_data={"node_id": node.get("id")},
                help_text="Generate a temporary 8-character pairing code for remote device attachment.",
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-nodes-refresh":
            self.refresh_nodes()
        elif btn_id == "btn-node-claim":
            self.post_message(self.NodeAction("claim"))
        elif btn_id == "btn-node-pair-code":
            self.post_message(self.NodeAction("pair_code", self.selected_node))
        elif btn_id == "btn-node-liveness" and self.selected_node:
            self.post_message(self.NodeAction("liveness", self.selected_node))
        elif btn_id == "btn-node-revoke" and self.selected_node:
            self.post_message(self.NodeAction("revoke", self.selected_node))
