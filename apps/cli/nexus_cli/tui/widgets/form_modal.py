"""Interactive Parameter Form Modal for commands requiring arguments and options."""

from typing import Any, Dict, Optional, Tuple

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from ...registry import CommandMetadata


class ParameterFormModal(ModalScreen[Optional[Tuple[Dict[str, Any], Dict[str, Any]]]]):
    """Dynamic form dialog for capturing command arguments prior to execution."""

    def __init__(self, command: CommandMetadata) -> None:
        super().__init__()
        self.command = command

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label(f"CONFIGURE: {self.command.name}", classes="modal-header")
            yield Static(f"[dim]{self.command.detailed_description}[/dim]", id="modal-desc")
            yield Static(f"[bold cyan]Syntax:[/bold cyan] {self.command.usage}\n")

            if self.command.is_destructive:
                prompt = self.command.destructive_prompt or "This is a destructive action that cannot be undone."
                yield Static(f"[bold red]WARNING:[/bold red] [yellow]{prompt}[/yellow]\n")

            # Arguments inputs
            for arg in self.command.args:
                req_str = " (Required)" if arg.required else " (Optional)"
                yield Label(f"{arg.name}{req_str}: {arg.description}")
                placeholder = f"Enter {arg.name}..."
                if arg.default is not None:
                    placeholder += f" [Default: {arg.default}]"
                yield Input(placeholder=placeholder, id=f"arg_{arg.name}")

            # Options inputs
            for opt in self.command.options:
                if not opt.is_flag:
                    yield Label(f"{opt.name}: {opt.description}")
                    yield Input(placeholder=f"Value for {opt.name}...", id=f"opt_{opt.name.lstrip('-')}")

            with Horizontal(classes="modal-footer"):
                if self.command.is_destructive:
                    yield Button("Confirm & Execute", variant="error", id="btn-submit", classes="modal-button")
                else:
                    yield Button("Execute", variant="primary", id="btn-submit", classes="modal-button")
                yield Button("Cancel", variant="default", id="btn-cancel", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
            return

        if event.button.id == "btn-submit":
            args_dict: Dict[str, Any] = {}
            opts_dict: Dict[str, Any] = {}

            # Gather args
            for arg in self.command.args:
                inp = self.query_one(f"#arg_{arg.name}", Input)
                val = inp.value.strip()
                if not val and arg.default is not None:
                    val = str(arg.default)
                if val:
                    if arg.type == "int":
                        try:
                            args_dict[arg.name] = int(val)
                        except ValueError:
                            args_dict[arg.name] = val
                    else:
                        args_dict[arg.name] = val

            # Gather options
            for opt in self.command.options:
                if not opt.is_flag:
                    opt_id = opt.name.lstrip("-")
                    try:
                        inp = self.query_one(f"#opt_{opt_id}", Input)
                        val = inp.value.strip()
                        if val:
                            opts_dict[opt_id] = val
                    except Exception:
                        pass

            self.dismiss((args_dict, opts_dict))

    def key_escape(self) -> None:
        self.dismiss(None)
