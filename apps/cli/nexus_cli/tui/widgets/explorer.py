"""Command Explorer Widget providing filtered discovery and selection of operations."""

from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import DataTable, Input, Label, Static

from ...registry import CommandCategory, CommandMetadata, get_registry


class CommandExplorer(Static):
    """Explorer table for inspecting, filtering, and activating commands."""

    class CommandSelected(Message):
        """Dispatched when a command row is highlighted or selected."""

        def __init__(self, command: CommandMetadata) -> None:
            self.command = command
            super().__init__()

    class CommandActivated(Message):
        """Dispatched when a command row is triggered via Enter/Double click."""

        def __init__(self, command: CommandMetadata) -> None:
            self.command = command
            super().__init__()

    current_category: Optional[CommandCategory] = None
    _commands_map: dict[str, CommandMetadata] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="explorer-container"):
            with Horizontal(id="explorer-header-row"):
                yield Label("COMMANDS", id="explorer-title")
                yield Input(placeholder="Type to filter commands... (/) ", id="command-filter-input")
            table = DataTable(id="commands-table", cursor_type="row")
            table.zebra_stripes = True
            yield table

    def on_mount(self) -> None:
        table = self.query_one("#commands-table", DataTable)
        table.add_columns("Command", "Summary", "Auth", "Destructive")
        self.load_category(CommandCategory.OVERVIEW)

    def load_category(self, category: CommandCategory) -> None:
        self.current_category = category
        self.query_one("#explorer-title", Label).update(category.value.upper())
        self.refresh_table()

    def refresh_table(self, query: str = "") -> None:
        table = self.query_one("#commands-table", DataTable)
        table.clear()
        self._commands_map.clear()

        reg = get_registry()
        if self.current_category:
            cmds = reg.list_by_category(self.current_category)
        else:
            cmds = reg.list_all()

        q = query.strip().lower()
        first_cmd: Optional[CommandMetadata] = None

        for cmd in cmds:
            if q and (
                q not in cmd.name.lower()
                and q not in cmd.summary.lower()
                and q not in " ".join(cmd.command_tokens).lower()
            ):
                continue

            self._commands_map[cmd.id] = cmd
            if first_cmd is None:
                first_cmd = cmd

            auth_badge = "🔒 Required" if cmd.requires_auth else "Free"
            dest_badge = "⚠️ Destructive" if cmd.is_destructive else "Safe"
            cmd_syntax = "nexus " + " ".join(cmd.command_tokens)

            table.add_row(
                f"[bold cyan]{cmd.name}[/bold cyan]\n[dim]{cmd_syntax}[/dim]",
                cmd.summary,
                auth_badge,
                dest_badge,
                key=cmd.id,
            )

        if first_cmd:
            self.post_message(self.CommandSelected(first_cmd))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "command-filter-input":
            self.refresh_table(query=event.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value in self._commands_map:
            cmd = self._commands_map[event.row_key.value]
            self.post_message(self.CommandSelected(cmd))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value in self._commands_map:
            cmd = self._commands_map[event.row_key.value]
            self.post_message(self.CommandActivated(cmd))
