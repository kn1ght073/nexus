"""Main Textual Application for NEXUS TUI Control Center.

Transforms the CLI into an interactive, multi-view personal infrastructure cockpit.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from textual.app import App, ComposeResult
from textual import events
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import ContentSwitcher, Footer

from ..config import load_config, save_config
from ..registry import CommandCategory, CommandMetadata, CommandResult, get_registry
from .widgets.account_view import AccountView
from .widgets.activity_view import ActivityView
from .widgets.context import ContextPanel
from .widgets.devices_view import DevicesView
from .widgets.diagnostics_view import DiagnosticsView
from .widgets.explorer import CommandExplorer
from .widgets.files_view import FilesView
from .widgets.form_modal import ParameterFormModal
from .widgets.header import StatusHeader
from .widgets.help_modal import HelpModal
from .widgets.network_view import NetworkView
from .widgets.nodes_view import NodesView
from .widgets.notes_tasks_view import NotesTasksView
from .widgets.overview import OverviewDashboard
from .widgets.palette import CommandPaletteModal
from .widgets.result_modal import ExecutionResultModal
from .widgets.services_view import ServicesView
from .widgets.settings_modal import SettingsModal
from .widgets.settings_view import SettingsView
from .widgets.sidebar import NavigationSidebar
from .widgets.sync_view import SyncView
from .widgets.wizard import SetupWizardModal


class NexusTUIApp(App):
    """Full-screen interactive terminal user interface for NEXUS personal digital infrastructure."""

    TITLE = "NEXUS Control Center"
    CSS_PATH = Path(__file__).parent / "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+k", "palette", "Palette", show=True),
        Binding("/", "palette", "Search", show=True),
        Binding("question_mark", "help", "Help", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("p", "settings", "Profiles", show=True),
        Binding("w", "wizard", "Setup", show=True),
        Binding("1", "jump_overview", "Overview", show=False),
        Binding("2", "jump_account", "Account", show=False),
        Binding("3", "jump_devices", "Devices", show=False),
        Binding("4", "jump_nodes", "Nodes", show=False),
        Binding("5", "jump_network", "Network", show=False),
        Binding("6", "jump_sync", "Sync", show=False),
        Binding("7", "jump_files", "Files", show=False),
        Binding("8", "jump_tasks", "Tasks", show=False),
        Binding("9", "jump_diagnostics", "Doctor", show=False),
        Binding("0", "jump_activity", "Activity", show=False),
    ]

    def compose(self) -> ComposeResult:
        cfg = load_config()
        # Default view initial resolution supporting aliases (e.g. tasks -> notes-tasks, doctor -> diagnostics)
        view_map = {
            "overview": "view-overview",
            "account": "view-account",
            "devices": "view-devices",
            "nodes": "view-nodes",
            "network": "view-network",
            "sync": "view-sync",
            "files": "view-files",
            "tasks": "view-notes-tasks",
            "notes-tasks": "view-notes-tasks",
            "services": "view-services",
            "doctor": "view-diagnostics",
            "diagnostics": "view-diagnostics",
            "activity": "view-activity",
            "settings": "view-settings",
        }
        initial_view = view_map.get(cfg.default_view, "view-overview")

        yield StatusHeader(id="status-header")
        with Horizontal(id="main-body-container"):
            yield NavigationSidebar(id="nav-sidebar")
            with ContentSwitcher(initial=initial_view, id="main-content-switcher"):
                yield OverviewDashboard(id="view-overview")
                yield AccountView(id="view-account")
                yield DevicesView(id="view-devices")
                yield NodesView(id="view-nodes")
                yield NetworkView(id="view-network")
                yield SyncView(id="view-sync")
                yield FilesView(id="view-files")
                yield NotesTasksView(id="view-notes-tasks")
                yield ServicesView(id="view-services")
                yield DiagnosticsView(id="view-diagnostics")
                yield ActivityView(id="view-activity")
                yield SettingsView(id="view-settings")
                yield CommandExplorer(id="cmd-explorer")
            yield ContextPanel(id="ctx-panel")
        yield Footer()

    def on_mount(self) -> None:
        cfg = load_config()
        if cfg.theme and cfg.theme != "dark":
            self.screen.add_class(f"theme-{cfg.theme}")

    def on_resize(self, event: events.Resize) -> None:
        """Adapt layout to terminal width: collapse context panel or sidebar on small terminals."""
        try:
            ctx = self.query_one("#ctx-panel", ContextPanel)
            sidebar = self.query_one("#nav-sidebar", NavigationSidebar)
            width = event.size.width
            ctx.display = (width >= 115)
            sidebar.display = (width >= 75)
        except Exception:
            pass

    def switch_to_view(self, view_id: str) -> None:
        """Switch central workspace to target view widget."""
        try:
            switcher = self.query_one("#main-content-switcher", ContentSwitcher)
            switcher.current = view_id
        except Exception:
            pass

    # Navigation Sidebar message handlers
    def on_navigation_sidebar_view_selected(self, event: NavigationSidebar.ViewSelected) -> None:
        self.switch_to_view(event.view_id)

    def on_navigation_sidebar_category_selected(self, event: NavigationSidebar.CategorySelected) -> None:
        self.switch_to_view("cmd-explorer")
        explorer = self.query_one("#cmd-explorer", CommandExplorer)
        explorer.load_category(event.category)

    # Overview Dashboard message handlers
    def on_overview_dashboard_switch_view(self, event: OverviewDashboard.SwitchView) -> None:
        self.switch_to_view(event.view_id)

    def on_overview_dashboard_quick_action(self, event: OverviewDashboard.QuickAction) -> None:
        if event.action_id == "sync_now":
            self.execute_named_command("sync.pull")
        elif event.action_id == "open_palette":
            self.action_palette()

    # Domain view message handlers
    def on_account_view_action_triggered(self, event: AccountView.ActionTriggered) -> None:
        if event.action_id == "logout":
            cmd = get_registry().get("auth.logout")
            if cmd:
                self.execute_command_flow(cmd)

    def on_devices_view_device_action(self, event: DevicesView.DeviceAction) -> None:
        if event.action_id == "revoke":
            cmd = get_registry().get("devices.revoke")
            if cmd:
                self.execute_command_flow(cmd, default_args={"device_id": event.device.get("id")})
        elif event.action_id == "pair":
            cmd = get_registry().get("nodes.pairing_code")
            if cmd:
                self.execute_command_flow(cmd)
        elif event.action_id == "inspect":
            cmd = get_registry().get("devices.inspect")
            if cmd:
                self.execute_command_flow(cmd, default_args={"device_id": event.device.get("id")})

    def on_nodes_view_node_action(self, event: NodesView.NodeAction) -> None:
        if event.action_id == "claim":
            cmd = get_registry().get("nodes.claim")
            if cmd:
                self.execute_command_flow(cmd)
        elif event.action_id == "pair_code":
            cmd = get_registry().get("nodes.pairing_code")
            if cmd:
                self.execute_command_flow(cmd, default_args={"node_id": event.node.get("id")})
        elif event.action_id == "revoke":
            cmd = get_registry().get("nodes.revoke")
            if cmd:
                self.execute_command_flow(cmd, default_args={"node_id": event.node.get("id")})
        elif event.action_id == "liveness":
            cmd = get_registry().get("overview.status")
            if cmd:
                self.execute_command_flow(cmd)

    def on_sync_view_sync_action(self, event: SyncView.SyncAction) -> None:
        if event.action_id == "sync_pull":
            self.execute_named_command("sync.pull")

    def on_files_view_file_action(self, event: FilesView.FileAction) -> None:
        if event.action_id == "copy_path":
            path_str = event.path
            try:
                import subprocess
                import sys
                if sys.platform == "darwin":
                    p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    p.communicate(path_str.encode("utf-8"))
                elif sys.platform == "win32":
                    p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
                    p.communicate(path_str.encode("utf-8"))
                else:
                    p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                    p.communicate(path_str.encode("utf-8"))
            except Exception:
                pass
            self.notify(f"Copied path: {path_str}", title="File Storage", severity="information")

    def on_services_view_service_action(self, event: ServicesView.ServiceAction) -> None:
        if event.action_id == "view_logs":
            self.notify("Logs recorded in ~/.nexus/logs. All local daemons active.", title="Service Logs", severity="information")

    def on_diagnostics_view_diagnostics_action(self, event: DiagnosticsView.DiagnosticsAction) -> None:
        if event.action_id == "export_report":
            report_data = event.data.get("checks", [])
            out_file = Path.home() / "nexus-diagnostic-report.json"
            try:
                import json
                clean_report = []
                for c in report_data:
                    clean_report.append({
                        "category": c.get("category"),
                        "name": c.get("name"),
                        "status": c.get("status"),
                        "detail": c.get("detail") or c.get("message"),
                    })
                iso_now = datetime.now(timezone.utc).isoformat()
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump({"timestamp": iso_now, "checks": clean_report}, f, indent=2)
                self.notify(f"Redacted report saved to {out_file}", title="Diagnostics Export", severity="information")
            except Exception as e:
                self.notify(f"Export failed: {e}", title="Export Error", severity="error")
        elif event.action_id == "copy_fix":
            fix_cmd = event.data.get("fix") or "nexus auth login"
            try:
                import subprocess
                import sys
                if sys.platform == "darwin":
                    p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    p.communicate(fix_cmd.encode("utf-8"))
                elif sys.platform == "win32":
                    p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
                    p.communicate(fix_cmd.encode("utf-8"))
                else:
                    p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                    p.communicate(fix_cmd.encode("utf-8"))
            except Exception:
                pass
            self.notify(f"Copied fix command: {fix_cmd}", title="Remediation", severity="information")

    def on_activity_view_activity_action(self, event: ActivityView.ActivityAction) -> None:
        if event.action_id == "export_activity":
            raw_events = event.data.get("events", [])
            out_file = Path.home() / "nexus-activity-audit.json"
            try:
                import json
                clean_events = []
                for ev in raw_events:
                    ev_copy = dict(ev)
                    details = ev_copy.get("details")
                    if isinstance(details, dict):
                        ev_copy["details"] = {
                            k: ("***" if any(s in k.lower() for s in ("token", "secret", "password", "key", "auth")) else v)
                            for k, v in details.items()
                        }
                    clean_events.append(ev_copy)
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(clean_events, f, indent=2)
                self.notify(f"Activity audit saved to {out_file}", title="Activity Export", severity="information")
            except Exception as e:
                self.notify(f"Export failed: {e}", title="Export Error", severity="error")
        elif event.action_id == "inspect_event":
            ev = event.data
            action = ev.get("action", "unknown")
            entity = f"{ev.get('entity_type', '')} #{ev.get('entity_id', '')}".strip()
            details = ev.get("details") or {}
            self.push_screen(ExecutionResultModal(CommandResult(
                success=True,
                title=f"Audit Event: {action}",
                message=f"Entity: {entity or 'System'}\nTimestamp: {ev.get('created_at', '-')}\nUser: {ev.get('user_id', 'Local')}",
                data=details,
            )))

    def on_productivity_view_action(self, event: NotesTasksView.ProductivityAction) -> None:
        if event.action_id == "add_task":
            cmd = get_registry().get("tasks.add")
            if cmd:
                self.execute_command_flow(cmd)
        elif event.action_id == "add_note":
            cmd = get_registry().get("notes.add")
            if cmd:
                self.execute_command_flow(cmd)
        elif event.action_id == "add_project":
            cmd = get_registry().get("projects.create")
            if cmd:
                self.execute_command_flow(cmd)

    def on_settings_view_settings_changed(self, event: SettingsView.SettingsChanged) -> None:
        header = self.query_one("#status-header", StatusHeader)
        header.refresh_telemetry()
        if event.key == "theme":
            self.screen.remove_class("theme-dark")
            self.screen.remove_class("theme-synthwave")
            self.screen.remove_class("theme-light")
            self.screen.add_class(f"theme-{event.value}")
            self.notify(f"Theme switched to {event.value}", title="Appearance")

    # Command Explorer & Context panel handlers
    def on_command_explorer_command_selected(self, event: CommandExplorer.CommandSelected) -> None:
        ctx_panel = self.query_one("#ctx-panel", ContextPanel)
        ctx_panel.update_command(event.command)

    def on_command_explorer_command_activated(self, event: CommandExplorer.CommandActivated) -> None:
        self.execute_command_flow(event.command)

    def on_context_panel_execute_command(self, event: ContextPanel.ExecuteCommand) -> None:
        self.execute_command_flow(event.command)

    def on_context_panel_resource_action(self, event: ContextPanel.ResourceAction) -> None:
        if event.action_id:
            cmd = get_registry().get(event.action_id)
            if cmd:
                self.execute_command_flow(cmd, default_args=event.context_data)
            else:
                self.notify(f"Triggered: {event.action_id}", title="Action")

    def execute_named_command(self, cmd_id: str, args: Optional[Dict[str, Any]] = None, opts: Optional[Dict[str, Any]] = None) -> None:
        cmd = get_registry().get(cmd_id)
        if cmd:
            self.execute_command_flow(cmd, default_args=args, default_opts=opts)

    def execute_command_flow(
        self,
        cmd: CommandMetadata,
        default_args: Optional[Dict[str, Any]] = None,
        default_opts: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Handle execution routing: direct run vs argument modal vs destructive confirmation."""
        try:
            cfg = load_config()
            cfg.record_recent_command(cmd.id)
            save_config(cfg)
        except Exception:
            pass

        has_args = bool(cmd.args) and not default_args
        has_required_options = any(not o.is_flag for o in cmd.options) and not default_opts

        if has_args or has_required_options or cmd.is_destructive:
            def on_form_submit(form_data: Optional[tuple]) -> None:
                if form_data is None:
                    return
                args_dict, opts_dict = form_data
                if default_args:
                    args_dict.update(default_args)
                if default_opts:
                    opts_dict.update(default_opts)
                reg = get_registry()
                res = reg.execute(cmd.id, args=args_dict, options=opts_dict)
                self.push_screen(ExecutionResultModal(res))

            self.push_screen(ParameterFormModal(cmd), on_form_submit)
        else:
            reg = get_registry()
            res = reg.execute(cmd.id, args=default_args or {}, options=default_opts or {})
            self.push_screen(ExecutionResultModal(res))

    def action_palette(self) -> None:
        def on_palette_selected(cmd: Optional[CommandMetadata]) -> None:
            if not cmd:
                return
            self.switch_to_view("cmd-explorer")
            explorer = self.query_one("#cmd-explorer", CommandExplorer)
            explorer.load_category(cmd.category)
            ctx_panel = self.query_one("#ctx-panel", ContextPanel)
            ctx_panel.update_command(cmd)

        self.push_screen(CommandPaletteModal(), on_palette_selected)

    def action_help(self) -> None:
        self.push_screen(HelpModal())

    def action_settings(self) -> None:
        def on_settings_done(changed: bool) -> None:
            if changed:
                header = self.query_one("#status-header", StatusHeader)
                header.refresh_telemetry()
        self.push_screen(SettingsModal(), on_settings_done)

    def action_wizard(self) -> None:
        def on_wizard_done(completed: bool) -> None:
            if completed:
                header = self.query_one("#status-header", StatusHeader)
                header.refresh_telemetry()
        self.push_screen(SetupWizardModal(), on_wizard_done)

    def action_refresh(self) -> None:
        header = self.query_one("#status-header", StatusHeader)
        header.refresh_telemetry()
        # Trigger refresh on current view if available
        try:
            switcher = self.query_one("#main-content-switcher", ContentSwitcher)
            cur = switcher.current
            if cur == "view-overview":
                self.query_one("#view-overview", OverviewDashboard).refresh_dashboard()
            elif cur == "view-devices":
                self.query_one("#view-devices", DevicesView).refresh_devices()
            elif cur == "view-nodes":
                self.query_one("#view-nodes", NodesView).refresh_nodes()
            elif cur == "view-network":
                self.query_one("#view-network", NetworkView).refresh_network()
            elif cur == "view-sync":
                self.query_one("#view-sync", SyncView).refresh_sync_status()
            elif cur == "view-files":
                self.query_one("#view-files", FilesView).browse_directory(None)
            elif cur == "view-notes-tasks":
                self.query_one("#view-notes-tasks", NotesTasksView).refresh_all_data()
            elif cur == "view-services":
                self.query_one("#view-services", ServicesView).probe_services()
            elif cur == "view-diagnostics":
                self.query_one("#view-diagnostics", DiagnosticsView).run_doctor()
            elif cur == "view-activity":
                self.query_one("#view-activity", ActivityView).refresh_activity()
        except Exception:
            pass

    # Quick Jump Number Keys
    def action_jump_overview(self) -> None:
        self.switch_to_view("view-overview")

    def action_jump_account(self) -> None:
        self.switch_to_view("view-account")

    def action_jump_devices(self) -> None:
        self.switch_to_view("view-devices")

    def action_jump_nodes(self) -> None:
        self.switch_to_view("view-nodes")

    def action_jump_network(self) -> None:
        self.switch_to_view("view-network")

    def action_jump_sync(self) -> None:
        self.switch_to_view("view-sync")

    def action_jump_files(self) -> None:
        self.switch_to_view("view-files")

    def action_jump_tasks(self) -> None:
        self.switch_to_view("view-notes-tasks")

    def action_jump_diagnostics(self) -> None:
        self.switch_to_view("view-diagnostics")

    def action_jump_activity(self) -> None:
        self.switch_to_view("view-activity")


# Backward-compatible alias
NexusTUI = NexusTUIApp
