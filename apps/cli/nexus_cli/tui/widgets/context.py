"""Context Panel Widget displaying command documentation, syntax, arguments, and execution trigger."""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import Button, Label, Static

from ...registry import CommandMetadata


class ContextPanel(Static):
    """Panel rendering rich metadata, parameters, and action controls for selected command."""

    class ExecuteCommand(Message):
        """Dispatched when the execute button is pressed."""

        def __init__(self, command: CommandMetadata) -> None:
            self.command = command
            super().__init__()

    current_command: Optional[CommandMetadata] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="context-container"):
            yield Label("COMMAND DETAILS", id="context-title")
            yield Static("Select a command from the explorer to view context.", id="context-content")
            with Container(id="context-actions"):
                yield Button("▶ Execute Command", id="btn-run", classes="btn-execute")

    def update_command(self, cmd: CommandMetadata) -> None:
        self.current_command = cmd
        content_lines = []

        content_lines.append(f"[bold cyan]{cmd.name}[/bold cyan]")
        content_lines.append(f"[dim]Category: {cmd.category.value}[/dim]")
        content_lines.append("")
        content_lines.append(f"[bold white]{cmd.summary}[/bold white]")
        content_lines.append("")
        content_lines.append(f"[dim]{cmd.detailed_description}[/dim]")
        content_lines.append("")
        content_lines.append("[bold]Usage Syntax:[/bold]")
        content_lines.append(f"  [cyan]{cmd.usage}[/cyan]")
        content_lines.append("")

        if cmd.args:
            content_lines.append("[bold]Arguments:[/bold]")
            for a in cmd.args:
                req = "[red]required[/red]" if a.required else "[dim]optional[/dim]"
                content_lines.append(f"• [cyan]{a.name}[/cyan] ({a.type}, {req}): {a.description}")
            content_lines.append("")

        if cmd.options:
            content_lines.append("[bold]Options:[/bold]")
            for o in cmd.options:
                flag = f" ({o.flag})" if o.flag else ""
                content_lines.append(f"• [cyan]{o.name}[/cyan]{flag}: {o.description}")
            content_lines.append("")

        if cmd.is_destructive:
            content_lines.append("[bold red]⚠️ DESTRUCTIVE OPERATION[/bold red]")
            if cmd.destructive_prompt:
                content_lines.append(f"[yellow]{cmd.destructive_prompt}[/yellow]")
            content_lines.append("")

        auth_note = "🔒 Requires authentication" if cmd.requires_auth else "🌐 Publicly accessible"
        content_lines.append(f"[dim]{auth_note}[/dim]")

        self.query_one("#context-content", Static).update("\n".join(content_lines))

        btn = self.query_one("#btn-run", Button)
        if cmd.is_destructive:
            btn.label = "⚠️ Run Destructive Command"
            btn.remove_class("btn-execute")
            btn.add_class("btn-destructive")
        else:
            btn.label = "▶ Execute Command"
            btn.remove_class("btn-destructive")
            btn.add_class("btn-execute")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-run" and self.current_command:
            self.post_message(self.ExecuteCommand(self.current_command))
