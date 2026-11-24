"""Account and Sovereign Identity Center Widget for NEXUS Control Center."""

from datetime import datetime
from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, DataTable, Label, Static, Switch

from ...client import get_client
from ...config import load_config, mask_email_address, save_config


class AccountView(Static):
    """Dedicated Account & Identity view showing sovereign identity, sessions, and privacy controls."""

    class ActionTriggered(Message):
        def __init__(self, action_id: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.action_id = action_id
            self.data = data or {}
            super().__init__()

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="account-scroll-container"):
            with Horizontal(classes="view-header-bar"):
                yield Label("👤 ACCOUNT & SOVEREIGN IDENTITY", classes="view-title")
                with Horizontal(classes="header-actions"):
                    yield Button("🔄 Refresh", id="btn-account-refresh", classes="btn-sm")
                    yield Button("🚪 Logout", id="btn-account-logout", variant="error", classes="btn-sm")

            # Privacy & Preferences Bar
            with Horizontal(id="account-privacy-bar", classes="config-bar"):
                yield Label("Privacy Mode — Mask Email Address in UI:", classes="config-label")
                yield Switch(id="switch-mask-email")

            # Split details
            with Horizontal(classes="details-row"):
                with Vertical(classes="details-box", id="box-identity-info"):
                    yield Label("SOVEREIGN CREDENTIALS", classes="box-title")
                    yield Static("Loading identity details...", id="identity-details-static")

                with Vertical(classes="details-box", id="box-oauth-info"):
                    yield Label("LINKED IDENTITY PROVIDERS", classes="box-title")
                    yield Static("Checking Google & GitHub status...", id="oauth-details-static")

            # Entity tallies
            with Vertical(classes="overview-full-card", id="box-entity-tallies"):
                yield Label("SOVEREIGN DATA INVENTORY", classes="card-header")
                yield Static("Loading data metrics...", id="entity-tallies-static")

            # Active Sessions & Linked Devices
            with Vertical(classes="overview-full-card", id="box-sessions"):
                yield Label("ACTIVE SESSIONS & AUTHORIZED CLIENTS", classes="card-header")
                table = DataTable(id="account-sessions-table", cursor_type="row")
                table.zebra_stripes = True
                yield table

    def on_mount(self) -> None:
        table = self.query_one("#account-sessions-table", DataTable)
        table.add_columns("Device", "Platform", "Status", "Last Active", "Client Type")
        
        cfg = load_config()
        sw = self.query_one("#switch-mask-email", Switch)
        sw.value = cfg.mask_email

        self.refresh_account()

    def refresh_account(self) -> None:
        self.run_worker(self._fetch_account_data, thread=True)

    def _fetch_account_data(self) -> None:
        client = get_client()
        cfg = load_config()

        acc = {}
        try:
            r = client.get("/api/account/overview", timeout=4)
            if r.status_code == 200:
                acc = r.json()
        except Exception:
            pass

        data_summary = {}
        try:
            r = client.get("/api/account/data-summary", timeout=4)
            if r.status_code == 200:
                data_summary = r.json()
        except Exception:
            pass

        github_info = {}
        try:
            r = client.get("/api/github/status", timeout=4)
            if r.status_code == 200:
                github_info = r.json()
        except Exception:
            pass

        devices = []
        try:
            r = client.get("/api/devices", timeout=4)
            if r.status_code == 200:
                devices = r.json()
        except Exception:
            pass

        self.app.call_from_thread(self._render_account_data, {
            "cfg": cfg,
            "account": acc,
            "data_summary": data_summary,
            "github": github_info,
            "devices": devices,
        })

    def _render_account_data(self, data: Dict[str, Any]) -> None:
        if not self.is_mounted:
            return
        cfg = data["cfg"]
        acc = data["account"]
        summary = data["data_summary"]
        gh = data["github"]
        devices = data["devices"]

        email = cfg.email or acc.get("email") or "Unauthenticated"
        if cfg.mask_email and "@" in email:
            email_display = mask_email_address(email)
        else:
            email_display = email

        created = (acc.get("created_at") or "")[:19].replace("T", " ") or "N/A"
        active_status = "[green]Active / Verified[/green]" if acc.get("is_active", True) else "[red]Suspended[/red]"

        id_lines = [
            f"[bold cyan]User Identity:[/bold cyan] {email_display}",
            f"[bold cyan]Account ID:[/bold cyan] {acc.get('account_id') or 'N/A'}",
            f"[bold cyan]Role:[/bold cyan] {(acc.get('role') or 'user').upper()}",
            f"[bold cyan]Status:[/bold cyan] {active_status}",
            f"[bold cyan]Registered Date:[/bold cyan] {created}",
            f"[bold cyan]Active Profile:[/bold cyan] {cfg.active_profile}",
            f"[bold cyan]Endpoint:[/bold cyan] {cfg.api_url}",
        ]
        try:
            self.query_one("#identity-details-static", Static).update("\n".join(id_lines))
        except Exception:
            pass

        google_ident = acc.get("google_identity") or {}
        g_name = google_ident.get("name", "Connected") if google_ident else "Not Linked"
        gh_user = gh.get("username") or ("Linked" if gh.get("connected") else "Not Linked")

        oauth_lines = [
            f"[bold cyan]Google OAuth 2.0:[/bold cyan] {'[green]● Linked[/green]' if google_ident else '[dim]○ Unlinked[/dim]'}",
            f"  • Profile Name: {g_name}",
            f"  • Scope: OpenID, Profile, Email",
            f"[bold cyan]GitHub OAuth:[/bold cyan] {'[green]● Linked[/green]' if gh.get('connected') else '[dim]○ Unlinked[/dim]'}",
            f"  • Username: {gh_user}",
            f"  • Sync: {'Enabled' if gh.get('sync_enabled') else 'Manual'}",
            f"[bold cyan]Credential Vault:[/bold cyan] [green]Encrypted in OS Keyring[/green]",
        ]
        try:
            self.query_one("#oauth-details-static", Static).update("\n".join(oauth_lines))
        except Exception:
            pass

        entities = summary.get("supported_entities", {})
        tally_lines = [
            f"[bold]Projects:[/bold] [cyan]{entities.get('projects', 0)}[/cyan]  |  "
            f"[bold]Tasks:[/bold] [cyan]{entities.get('tasks', 0)}[/cyan]  |  "
            f"[bold]Notes:[/bold] [cyan]{entities.get('notes', 0)}[/cyan]  |  "
            f"[bold]Inbox Items:[/bold] [cyan]{entities.get('inbox_items', 0)}[/cyan]",
            f"[dim]Retention Policy: Sovereign local preservation with incremental delta synchronisation.[/dim]",
        ]
        try:
            self.query_one("#entity-tallies-static", Static).update("\n".join(tally_lines))
        except Exception:
            pass

        try:
            table = self.query_one("#account-sessions-table", DataTable)
            table.clear()
            for d in devices:
                online = "[bold green]● online[/bold green]" if d.get("is_online") else "[dim]○ offline[/dim]"
                last_seen = (d.get("last_seen") or "")[:19].replace("T", " ")
                table.add_row(
                    d.get("name", "Unknown Device"),
                    d.get("platform", "-"),
                    online,
                    last_seen or "-",
                    "Hardware Edge Device",
                )
            if not devices:
                table.add_row("Current Machine", platform.system(), "[bold green]● online[/bold green]", "Active Now", "Local Interactive CLI")
        except Exception:
            pass

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "switch-mask-email":
            cfg = load_config()
            cfg.mask_email = event.value
            save_config(cfg)
            self.refresh_account()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-account-refresh":
            self.refresh_account()
        elif event.button.id == "btn-account-logout":
            self.post_message(self.ActionTriggered("logout"))
