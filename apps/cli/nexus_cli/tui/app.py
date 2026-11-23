"""Main Textual Application for NEXUS TUI Control Center."""

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Footer

from ..config import load_config, save_config
from ..registry import CommandCategory, CommandMetadata, CommandResult, get_registry
from .widgets.context import ContextPanel
from .widgets.explorer import CommandExplorer
from .widgets.form_modal import ParameterFormModal
from .widgets.header import StatusHeader
from .widgets.help_modal import HelpModal
from .widgets.palette import CommandPaletteModal
from .widgets.result_modal import ExecutionResultModal
from .widgets.settings_modal import SettingsModal
from .widgets.sidebar import NavigationSidebar
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
    ]

    def compose(self) -> ComposeResult:
        yield StatusHeader(id="status-header")
        with Horizontal(id="main-body-container"):
            yield NavigationSidebar(id="nav-sidebar")
            yield CommandExplorer(id="cmd-explorer")
            yield ContextPanel(id="ctx-panel")
        yield Footer()

    def on_navigation_sidebar_category_selected(self, event: NavigationSidebar.CategorySelected) -> None:
        explorer = self.query_one("#cmd-explorer", CommandExplorer)
        explorer.load_category(event.category)

    def on_command_explorer_command_selected(self, event: CommandExplorer.CommandSelected) -> None:
        ctx_panel = self.query_one("#ctx-panel", ContextPanel)
        ctx_panel.update_command(event.command)

    def on_command_explorer_command_activated(self, event: CommandExplorer.CommandActivated) -> None:
        self.execute_command_flow(event.command)

    def on_context_panel_execute_command(self, event: ContextPanel.ExecuteCommand) -> None:
        self.execute_command_flow(event.command)

    def execute_command_flow(self, cmd: CommandMetadata) -> None:
        """Handle execution routing: direct run vs argument modal vs destructive confirmation."""
        # Record into recent commands
        try:
            cfg = load_config()
            cfg.record_recent_command(cmd.id)
            save_config(cfg)
        except Exception:
            pass

        has_args = bool(cmd.args)
        has_required_options = any(not o.is_flag for o in cmd.options)

        if has_args or has_required_options or cmd.is_destructive:
            def on_form_submit(form_data: Optional[tuple]) -> None:
                if form_data is None:
                    return
                args_dict, opts_dict = form_data
                reg = get_registry()
                res = reg.execute(cmd.id, args=args_dict, options=opts_dict)
                self.push_screen(ExecutionResultModal(res))

            self.push_screen(ParameterFormModal(cmd), on_form_submit)
        else:
            reg = get_registry()
            res = reg.execute(cmd.id, args={}, options={})
            self.push_screen(ExecutionResultModal(res))

    def action_palette(self) -> None:
        def on_palette_selected(cmd: Optional[CommandMetadata]) -> None:
            if not cmd:
                return
            # Update explorer and context panel
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


# Backward-compatible alias
NexusTUI = NexusTUIApp
