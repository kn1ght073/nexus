"""Keyboard shortcuts help modal."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class HelpModal(ModalScreen[None]):
    """Modal displaying complete keyboard shortcuts cheat sheet."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label("KEYBOARD SHORTCUTS & NAVIGATION", classes="modal-header")
            help_text = """
[bold cyan]Global Shortcuts:[/bold cyan]
  [bold white]/[/bold white] or [bold white]Ctrl+K[/bold white]  : Open Global Command Palette & Fuzzy Search
  [bold white]?[/bold white]           : Toggle this Keyboard Help Screen
  [bold white]r[/bold white]           : Refresh Status, Ping & Telemetry
  [bold white]p[/bold white]           : Open Settings & Profile Switcher
  [bold white]w[/bold white]           : Launch Setup Wizard
  [bold white]q[/bold white]           : Quit TUI Application
  [bold white]Esc[/bold white]         : Close Modal / Clear Filter

[bold cyan]Panel Navigation:[/bold cyan]
  [bold white]Tab[/bold white]         : Move focus between Sidebar, Explorer, and Filter
  [bold white]Shift+Tab[/bold white]   : Move focus backwards
  [bold white]Up / Down[/bold white]   : Navigate list/table rows
  [bold white]Enter[/bold white]       : Activate / Execute selected item
"""
            yield Static(help_text)
            with Horizontal(classes="modal-footer"):
                yield Button("Got it (Esc)", variant="primary", id="btn-close", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
