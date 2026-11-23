"""Global Command Palette Modal supporting fuzzy searching and quick execution."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList
from textual.widgets.option_list import Option

from ...registry import CommandMetadata, get_registry


class CommandPaletteModal(ModalScreen[CommandMetadata]):
    """Modal command palette activated via Ctrl+K or /."""

    _results: list[CommandMetadata] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-box"):
            yield Label("COMMAND PALETTE — Search commands, categories, shortcuts", classes="modal-header")
            yield Input(placeholder="Type to search... (e.g. devices, auth, notes, config)", id="palette-search-input")
            yield OptionList(id="palette-results-list")

    def on_mount(self) -> None:
        self.update_results("")
        self.query_one("#palette-search-input", Input).focus()

    def update_results(self, query: str) -> None:
        reg = get_registry()
        self._results = reg.search(query)
        opt_list = self.query_one("#palette-results-list", OptionList)
        opt_list.clear_options()

        for cmd in self._results:
            dest_tag = " [DESTRUCTIVE]" if cmd.is_destructive else ""
            line = f"{cmd.name}  —  nexus {' '.join(cmd.command_tokens)}{dest_tag} ({cmd.category.value})"
            opt_list.add_option(Option(line, id=cmd.id))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "palette-search-input":
            self.update_results(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        opt_list = self.query_one("#palette-results-list", OptionList)
        if opt_list.highlighted is not None and opt_list.highlighted < len(self._results):
            self.dismiss(self._results[opt_list.highlighted])
        elif self._results:
            self.dismiss(self._results[0])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        cmd_id = event.option_id
        reg = get_registry()
        cmd = reg.get(cmd_id)
        if cmd:
            self.dismiss(cmd)

    def key_escape(self) -> None:
        self.dismiss(None)
