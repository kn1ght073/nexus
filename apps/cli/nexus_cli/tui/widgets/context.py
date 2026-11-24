"""Context Panel Widget displaying resource metadata, command documentation, and action controls."""

from typing import Any, Callable, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Label, Static

from ...registry import CommandMetadata


class ContextPanel(Static):
    """Panel rendering rich metadata, properties, and action controls for selected context."""

    class ExecuteCommand(Message):
        """Dispatched when the execute command button is pressed."""

        def __init__(self, command: CommandMetadata) -> None:
            self.command = command
            super().__init__()

    class ResourceAction(Message):
        """Dispatched when a contextual resource action button is pressed."""

        def __init__(self, action_id: str, context_data: Optional[Dict[str, Any]] = None) -> None:
            self.action_id = action_id
            self.context_data = context_data or {}
            super().__init__()

    current_command: Optional[CommandMetadata] = None
    current_resource_action: Optional[str] = None
    current_resource_data: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="context-container"):
            yield Label("CONTEXT & DETAILS", id="context-title")
            yield Static("Select an item, device, node, or command to inspect its context and actions.", id="context-content")
            with Container(id="context-actions"):
                yield Button("▶ Execute Command", id="btn-run", classes="btn-execute")

    def update_command(self, cmd: CommandMetadata) -> None:
        """Update context panel with selected CLI command metadata."""
        self.current_command = cmd
        self.current_resource_action = None
        self.current_resource_data = None

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
        btn.display = True
        if cmd.is_destructive:
            btn.label = "⚠️ Run Destructive Command"
            btn.remove_class("btn-execute")
            btn.add_class("btn-destructive")
        else:
            btn.label = "▶ Execute Command"
            btn.remove_class("btn-destructive")
            btn.add_class("btn-execute")

    def update_resource(
        self,
        title: str,
        subtitle: str,
        properties: Dict[str, Any],
        action_label: Optional[str] = None,
        action_id: Optional[str] = None,
        action_data: Optional[Dict[str, Any]] = None,
        is_destructive: bool = False,
        help_text: Optional[str] = None,
    ) -> None:
        """Update context panel with selected domain resource (Device, Node, Note, Task, etc.)."""
        self.current_command = None
        self.current_resource_action = action_id
        self.current_resource_data = action_data

        lines = [
            f"[bold cyan]{title}[/bold cyan]",
            f"[dim]{subtitle}[/dim]",
            "",
        ]

        if properties:
            lines.append("[bold]Properties:[/bold]")
            for k, v in properties.items():
                if v is None:
                    v_str = "[dim]-[/dim]"
                elif isinstance(v, bool):
                    v_str = "[green]Yes[/green]" if v else "[dim]No[/dim]"
                else:
                    v_str = f"[white]{v}[/white]"
                lines.append(f"• [cyan]{k}:[/cyan] {v_str}")
            lines.append("")

        if help_text:
            lines.append(f"[dim]{help_text}[/dim]")

        self.query_one("#context-content", Static).update("\n".join(lines))

        btn = self.query_one("#btn-run", Button)
        if action_label and action_id:
            btn.display = True
            btn.label = action_label
            if is_destructive:
                btn.remove_class("btn-execute")
                btn.add_class("btn-destructive")
            else:
                btn.remove_class("btn-destructive")
                btn.add_class("btn-execute")
        else:
            btn.display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-run":
            if self.current_command:
                self.post_message(self.ExecuteCommand(self.current_command))
            elif self.current_resource_action:
                self.post_message(self.ResourceAction(self.current_resource_action, self.current_resource_data))
