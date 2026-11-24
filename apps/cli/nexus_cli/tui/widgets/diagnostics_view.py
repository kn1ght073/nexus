"""Diagnostics Center Widget for NEXUS Control Center."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, DataTable, Label, Static

from ...commands.doctor import run_diagnostics
from ...config import load_config
from .context import ContextPanel


class DiagnosticsView(Static):
    """Doctor Diagnostics Center providing automated health audits, explanations, and export."""

    class DiagnosticsAction(Message):
        def __init__(self, action_id: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.action_id = action_id
            self.data = data or {}
            super().__init__()

    _checks_cache: List[Dict[str, Any]] = []
    _checks_by_id: Dict[str, Dict[str, Any]] = {}
    selected_check: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="diagnostics-container"):
            with Horizontal(classes="view-header-bar"):
                yield Label("🩺 SYSTEM DIAGNOSTICS & HEALTH AUDIT", classes="view-title")
                with Horizontal(classes="header-actions"):
                    yield Button("🔄 Re-run Diagnostics", id="btn-diag-run", variant="primary", classes="btn-sm")
                    yield Button("📄 Export Redacted Report", id="btn-diag-export", classes="btn-sm")

            with Horizontal(id="diagnostics-split-body"):
                # Left: Diagnostics Checks Table
                with Vertical(id="diag-table-container"):
                    table = DataTable(id="diagnostics-table", cursor_type="row")
                    table.zebra_stripes = True
                    yield table

                # Right: Check Explanation & Solution Details
                with Vertical(id="diag-details-card", classes="details-box"):
                    yield Label("DIAGNOSTIC AUDIT REPORT", classes="box-title")
                    yield Static("Select a diagnostic probe to inspect its health status and remediation.", id="diag-details-static")
                    with Horizontal(id="diag-action-buttons"):
                        yield Button("Copy Fix Command", id="btn-copy-fix", classes="btn-sm")

    def on_mount(self) -> None:
        table = self.query_one("#diagnostics-table", DataTable)
        table.add_columns("Category", "Check Name", "Status", "Summary")
        self.run_doctor()

    def run_doctor(self) -> None:
        self.run_worker(self._execute_diagnostics, thread=True)

    def _execute_diagnostics(self) -> None:
        results = run_diagnostics()
        checks = results.get("checks", [])
        self.app.call_from_thread(self._render_diagnostics, checks)

    def _render_diagnostics(self, checks: List[Dict[str, Any]]) -> None:
        if not self.is_mounted:
            return
        self._checks_cache = checks
        self._checks_by_id.clear()

        try:
            table = self.query_one("#diagnostics-table", DataTable)
        except Exception:
            return
        table.clear()

        first_key = None
        for i, c in enumerate(checks):
            cat = c.get("category", "General")
            name = c.get("name", "Unknown Check")
            st = c.get("status", "pass").lower()
            detail = c.get("detail") or c.get("message") or ""

            if st == "pass":
                badge = "[bold green]PASS[/bold green]"
            elif st == "warn":
                badge = "[bold yellow]WARN[/bold yellow]"
            elif st == "fail":
                badge = "[bold red]FAIL[/bold red]"
            else:
                badge = "[dim]SKIP[/dim]"

            key = f"chk_{i}_{name}"
            self._checks_by_id[key] = c
            if first_key is None:
                first_key = key

            table.add_row(
                cat,
                f"[bold cyan]{name}[/bold cyan]",
                badge,
                detail[:50],
                key=key,
            )

        if first_key and first_key in self._checks_by_id:
            self._display_check(self._checks_by_id[first_key])

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value in self._checks_by_id:
            c = self._checks_by_id[event.row_key.value]
            self._display_check(c)

    def _display_check(self, c: Dict[str, Any]) -> None:
        self.selected_check = c
        cat = c.get("category", "General")
        name = c.get("name", "Unknown")
        st = c.get("status", "pass").upper()
        detail = c.get("detail") or c.get("message") or "Check completed."

        color = "green" if st == "PASS" else ("yellow" if st == "WARN" else "red")

        lines = [
            f"[bold cyan]{name}[/bold cyan] ({cat})",
            f"Status: [{color}][bold]{st}[/bold][/{color}]",
            "",
            "[bold]Audit Details:[/bold]",
            f"  {detail}",
            "",
        ]

        if st in ("WARN", "FAIL"):
            lines.append("[bold yellow]Possible Cause:[/bold yellow]")
            cause = c.get("cause") or "Configuration missing, dependency not installed, or network host unreachable."
            lines.append(f"  {cause}")
            lines.append("")
            lines.append("[bold green]Suggested Remediation:[/bold green]")
            fix = c.get("fix") or "Run 'nexus auth login' or verify internet connectivity to control plane."
            lines.append(f"  {fix}")
            lines.append("")
        else:
            lines.append("[bold green]✔ Probe passed all security and operational invariants.[/bold green]")
            lines.append("")

        try:
            self.query_one("#diag-details-static", Static).update("\n".join(lines))
        except Exception:
            pass

        # Update context panel
        try:
            ctx = self.app.query_one(ContextPanel)
            ctx.update_resource(
                title=f"Diagnostic: {name}",
                subtitle=f"{cat} — {st}",
                properties={
                    "Status": st,
                    "Category": cat,
                    "Summary": detail[:40],
                },
                action_label="Run Doctor Diagnostics",
                action_id="doctor.run",
                help_text="Performs automated health checks across runtime, network, security, and storage.",
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-diag-run":
            self.run_doctor()
        elif btn_id == "btn-diag-export":
            self.post_message(self.DiagnosticsAction("export_report", {"checks": self._checks_cache}))
        elif btn_id == "btn-copy-fix" and self.selected_check:
            self.post_message(self.DiagnosticsAction("copy_fix", self.selected_check))
