"""Device Management Center Widget for NEXUS Control Center."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DataTable, Input, Label, Static

from ...client import get_client
from ...config import load_config
from .context import ContextPanel


class DevicesView(Static):
    """Device Explorer view showing hardware devices, status, telemetry, and lifecycle actions."""

    class DeviceAction(Message):
        def __init__(self, action_id: str, device: Dict[str, Any]) -> None:
            self.action_id = action_id
            self.device = device
            super().__init__()

    _devices_cache: List[Dict[str, Any]] = []
    _devices_by_id: Dict[str, Dict[str, Any]] = {}
    selected_device: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="devices-container"):
            with Horizontal(classes="view-header-bar"):
                yield Label("📱 DEVICE MANAGEMENT CENTER", classes="view-title")
                with Horizontal(classes="header-actions"):
                    yield Input(placeholder="Filter devices... (name, platform)", id="device-filter-input")
                    yield Button("🔄 Refresh", id="btn-devices-refresh", classes="btn-sm")
                    yield Button("➕ Pair Device", id="btn-device-pair", variant="primary", classes="btn-sm")

            with Horizontal(id="devices-split-body"):
                # Left pane: Device Table
                with Vertical(id="devices-table-container"):
                    table = DataTable(id="devices-table", cursor_type="row")
                    table.zebra_stripes = True
                    yield table

                # Right pane: Quick Details
                with Vertical(id="device-details-card", classes="details-box"):
                    yield Label("DEVICE INSPECTION", classes="box-title")
                    yield Static("Select a device from the table to inspect details.", id="device-details-static")
                    with Horizontal(id="device-action-buttons"):
                        yield Button("Inspect Full", id="btn-act-inspect", classes="btn-sm")
                        yield Button("Revoke Device", id="btn-act-revoke", variant="error", classes="btn-sm")

    def on_mount(self) -> None:
        table = self.query_one("#devices-table", DataTable)
        table.add_columns("ID", "Name", "Platform", "Status", "Last Seen", "Capabilities")
        self.refresh_devices()

    def refresh_devices(self, filter_q: str = "") -> None:
        self.run_worker(lambda: self._fetch_devices(filter_q), thread=True)

    def _fetch_devices(self, filter_q: str) -> None:
        client = get_client()
        devs = []
        try:
            r = client.get("/api/devices", timeout=4)
            if r.status_code == 200:
                devs = r.json()
        except Exception:
            pass

        self.app.call_from_thread(self._render_devices_table, devs, filter_q)

    def _render_devices_table(self, devs: List[Dict[str, Any]], filter_q: str) -> None:
        if not self.is_mounted:
            return
        self._devices_cache = devs
        self._devices_by_id.clear()

        try:
            table = self.query_one("#devices-table", DataTable)
        except Exception:
            return
        table.clear()

        q = filter_q.strip().lower()
        first_row_key = None

        for d in devs:
            name = d.get("name", "Unknown")
            plat = d.get("platform", "-")
            if q and (q not in name.lower() and q not in plat.lower()):
                continue

            dev_id = str(d.get("id"))
            self._devices_by_id[dev_id] = d
            if first_row_key is None:
                first_row_key = dev_id

            online = "[bold green]● online[/bold green]" if d.get("is_online") else "[dim]○ offline[/dim]"
            last_seen = (d.get("last_seen") or "")[:19].replace("T", " ")
            caps = ", ".join(d.get("capabilities", [])) or "standard"

            table.add_row(
                dev_id,
                f"[bold cyan]{name}[/bold cyan]",
                plat,
                online,
                last_seen or "-",
                caps,
                key=dev_id,
            )

        if first_row_key and first_row_key in self._devices_by_id:
            self._display_device(self._devices_by_id[first_row_key])

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "device-filter-input":
            self.refresh_devices(filter_q=event.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value in self._devices_by_id:
            dev = self._devices_by_id[event.row_key.value]
            self._display_device(dev)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value in self._devices_by_id:
            dev = self._devices_by_id[event.row_key.value]
            self.post_message(self.DeviceAction("inspect", dev))

    def _display_device(self, dev: Dict[str, Any]) -> None:
        self.selected_device = dev
        online_str = "[bold green]Online[/bold green]" if dev.get("is_online") else "[dim]Offline[/dim]"
        last_seen = (dev.get("last_seen") or "")[:19].replace("T", " ") or "N/A"
        created = (dev.get("created_at") or "")[:19].replace("T", " ") or "N/A"

        lines = [
            f"[bold cyan]{dev.get('name', 'Device')}[/bold cyan]",
            f"[dim]Device ID #{dev.get('id')}[/dim]",
            "",
            f"[bold]Platform:[/bold] {dev.get('platform', '-')}",
            f"[bold]Status:[/bold] {online_str}",
            f"[bold]Last Active:[/bold] {last_seen}",
            f"[bold]Registered At:[/bold] {created}",
            f"[bold]Capabilities:[/bold] {', '.join(dev.get('capabilities', [])) or 'None'}",
            f"[bold]Trust State:[/bold] [green]Authenticated Hardware[/green]",
            "",
            "[dim]Select an action below or press Enter to inspect.[/dim]",
        ]

        try:
            self.query_one("#device-details-static", Static).update("\n".join(lines))
        except Exception:
            pass

        # Update global ContextPanel as well
        try:
            ctx = self.app.query_one(ContextPanel)
            ctx.update_resource(
                title=f"Device: {dev.get('name')}",
                subtitle=f"ID #{dev.get('id')} — {dev.get('platform', 'Hardware')}",
                properties={
                    "Status": "Online" if dev.get("is_online") else "Offline",
                    "Last Active": last_seen,
                    "Platform": dev.get("platform", "-"),
                    "Registered": created,
                    "Capabilities": ", ".join(dev.get("capabilities", [])) or "Standard",
                },
                action_label="Revoke Device",
                action_id="devices.revoke",
                action_data={"device_id": dev.get("id"), "device_name": dev.get("name")},
                is_destructive=True,
                help_text="Revoking will permanently disconnect this device from your private mesh.",
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-devices-refresh":
            self.refresh_devices()
        elif btn_id == "btn-device-pair":
            self.post_message(self.DeviceAction("pair", {}))
        elif btn_id == "btn-act-inspect" and self.selected_device:
            self.post_message(self.DeviceAction("inspect", self.selected_device))
        elif btn_id == "btn-act-revoke" and self.selected_device:
            self.post_message(self.DeviceAction("revoke", self.selected_device))
