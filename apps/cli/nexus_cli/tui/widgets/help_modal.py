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
  [bold cyan]/[/bold cyan] or [bold cyan]Ctrl+K[/bold cyan]  : Open Global Command Palette & Fuzzy Search
  [bold cyan]?[/bold cyan]           : Toggle this Keyboard Help Screen
  [bold cyan]r[/bold cyan]           : Refresh Status, Ping & Telemetry
  [bold cyan]p[/bold cyan]           : Open Settings & Profile Switcher
  [bold cyan]w[/bold cyan]           : Launch Setup Wizard
  [bold cyan]q[/bold cyan]           : Quit TUI Application
  [bold cyan]Esc[/bold cyan]         : Close Modal / Clear Filter

[bold cyan]Panel Navigation:[/bold cyan]
  [bold cyan]Tab[/bold cyan]         : Move focus between Sidebar, Explorer, and Filter
  [bold cyan]Shift+Tab[/bold cyan]   : Move focus backwards
  [bold cyan]Up / Down[/bold cyan]   : Navigate list/table rows
  [bold cyan]Enter[/bold cyan]       : Activate / Execute selected item
"""
            yield Static(help_text)
            with Horizontal(classes="modal-footer"):
                yield Button("Got it (Esc)", variant="primary", id="btn-close", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
