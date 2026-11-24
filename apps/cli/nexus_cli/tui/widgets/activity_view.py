"""Activity and Security Center Widget for NEXUS Control Center."""

from datetime import datetime
import json
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DataTable, Input, Label, Static

from ...client import get_client
from ...config import load_config
from .context import ContextPanel


class ActivityView(Static):
    """Audit and Security Event Timeline with searching, category filtering, and export."""

    class ActivityAction(Message):
        def __init__(self, action_id: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.action_id = action_id
            self.data = data or {}
            super().__init__()

    _events_cache: List[Dict[str, Any]] = []
    _events_by_id: Dict[str, Dict[str, Any]] = {}
    selected_event: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="activity-container"):
            with Horizontal(classes="view-header-bar"):
                yield Label("🛡️ ACTIVITY & SECURITY AUDIT TIMELINE", classes="view-title")
                with Horizontal(classes="header-actions"):
                    yield Input(placeholder="Filter events... (auth, device, sync)", id="activity-filter-input")
                    yield Button("🔄 Refresh", id="btn-act-refresh", classes="btn-sm")
                    yield Button("📄 Export Audit", id="btn-act-export", classes="btn-sm")

            with Horizontal(id="activity-split-body"):
                # Left: Events Table
                with Vertical(id="activity-table-container"):
                    table = DataTable(id="activity-table", cursor_type="row")
                    table.zebra_stripes = True
                    yield table

                # Right: Event Detail Pane
                with Vertical(id="activity-details-card", classes="details-box"):
                    yield Label("AUDIT EVENT DETAILS", classes="box-title")
                    yield Static("Select an audit event from the table to inspect details.", id="activity-details-static")
                    with Horizontal(id="activity-action-buttons"):
                        yield Button("Inspect Payload", id="btn-act-inspect-payload", classes="btn-sm")

    def on_mount(self) -> None:
        table = self.query_one("#activity-table", DataTable)
        table.add_columns("Timestamp", "Action", "Entity", "User", "Summary")
        self.refresh_activity()

    def refresh_activity(self, filter_q: str = "") -> None:
        self.run_worker(lambda: self._fetch_activity(filter_q), thread=True)

    def _fetch_activity(self, filter_q: str) -> None:
        client = get_client()
        events = []
        try:
            r = client.get("/api/activity?limit=50", timeout=4)
            if r.status_code == 200:
                events = r.json()
        except Exception:
            pass

        self.app.call_from_thread(self._render_activity_table, events, filter_q)

    def _render_activity_table(self, events: List[Dict[str, Any]], filter_q: str) -> None:
        if not self.is_mounted:
            return
        self._events_cache = events
        self._events_by_id.clear()

        try:
            table = self.query_one("#activity-table", DataTable)
        except Exception:
            return
        table.clear()

        q = filter_q.strip().lower()
        first_key = None

        for ev in events:
            action = ev.get("action", "unknown")
            entity_type = ev.get("entity_type", "")
            summary = ev.get("summary") or ev.get("details") or f"Action {action}"

            if q and (q not in action.lower() and q not in entity_type.lower() and q not in summary.lower()):
                continue

            ev_id = str(ev.get("id"))
            self._events_by_id[ev_id] = ev
            if first_key is None:
                first_key = ev_id

            created = (ev.get("created_at") or "")[:19].replace("T", " ")
            user_str = str(ev.get("user_id", "System"))
            entity_str = f"{entity_type} #{ev.get('entity_id', '')}".strip()

            table.add_row(
                f"[dim]{created}[/dim]",
                f"[bold cyan]{action}[/bold cyan]",
                entity_str or "-",
                user_str,
                summary[:50],
                key=ev_id,
            )

        if not events:
            table.add_row(datetime.now().strftime("%Y-%m-%d %H:%M"), "system.online", "Core", "Local", "Connected to NEXUS")

        if first_key and first_key in self._events_by_id:
            self._display_event(self._events_by_id[first_key])

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "activity-filter-input":
            self.refresh_activity(filter_q=event.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value in self._events_by_id:
            ev = self._events_by_id[event.row_key.value]
            self._display_event(ev)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value in self._events_by_id:
            ev = self._events_by_id[event.row_key.value]
            self.post_message(self.ActivityAction("inspect_event", ev))

    def _display_event(self, ev: Dict[str, Any]) -> None:
        self.selected_event = ev
        created = (ev.get("created_at") or "")[:19].replace("T", " ") or "N/A"
        action = ev.get("action", "event")
        entity = f"{ev.get('entity_type', '')} #{ev.get('entity_id', '')}".strip()

        # Sanitize details (ensure no tokens/secrets)
        raw_details = ev.get("details") or {}
        if isinstance(raw_details, dict):
            clean_details = {k: ("***" if "token" in k or "key" in k or "secret" in k else v) for k, v in raw_details.items()}
            details_str = json.dumps(clean_details, indent=2)
        else:
            details_str = str(raw_details)

        lines = [
            f"[bold cyan]Action: {action}[/bold cyan]",
            f"[dim]Timestamp: {created}[/dim]",
            f"[bold]Target Entity:[/bold] {entity or 'Global / System'}",
            f"[bold]Author User ID:[/bold] {ev.get('user_id', 'Local')}",
            f"[bold]IP / Route:[/bold] {ev.get('ip_address', 'Localhost')}",
            "",
            "[bold]Audit Payload (Redacted):[/bold]",
            f"[dim]{details_str}[/dim]",
        ]

        try:
            self.query_one("#activity-details-static", Static).update("\n".join(lines))
        except Exception:
            pass

        # Update context panel
        try:
            ctx = self.app.query_one(ContextPanel)
            ctx.update_resource(
                title=f"Audit Event #{ev.get('id', '')}",
                subtitle=f"{action} at {created}",
                properties={
                    "Action": action,
                    "Entity": entity or "System",
                    "Timestamp": created,
                },
                action_label="Refresh Activity Log",
                action_id="activity.refresh",
                help_text="Immutable sovereign audit log of every mutating action.",
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-act-refresh":
            self.refresh_activity()
        elif btn_id == "btn-act-export":
            self.post_message(self.ActivityAction("export_activity", {"events": self._events_cache}))
        elif btn_id == "btn-act-inspect-payload" and self.selected_event:
            self.post_message(self.ActivityAction("inspect_event", self.selected_event))
