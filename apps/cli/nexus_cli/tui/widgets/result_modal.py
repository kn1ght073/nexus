"""Execution Result Modal displaying operation outcome, message, and JSON data."""

import json
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from ...registry import CommandResult


class ExecutionResultModal(ModalScreen[None]):
    """Modal displaying the result of a command execution."""

    def __init__(self, result: CommandResult) -> None:
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            title = self.result.title or ("SUCCESS" if self.result.success else "FAILURE")
            header_color = "green" if self.result.success else "red"
            yield Label(f"[{header_color}]{title}[/{header_color}]", classes="modal-header")

            if self.result.message:
                yield Static(self.result.message, id="result-message")

            if self.result.error:
                yield Static(f"[bold red]Error Details:[/bold red]\n{self.result.error}", id="result-error")

            if self.result.data:
                try:
                    formatted_json = json.dumps(self.result.data, indent=2, default=str)
                    yield Static(f"\n[bold cyan]Payload Data:[/bold cyan]\n[dim]{formatted_json}[/dim]", id="result-data")
                except Exception:
                    yield Static(f"\n[dim]{str(self.result.data)}[/dim]")

            with Horizontal(classes="modal-footer"):
                yield Button("Close (Esc)", variant="primary", id="btn-close", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
