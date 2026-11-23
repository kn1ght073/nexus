"""First-Time Setup Wizard Modal guiding user through initial configuration."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from ...client import get_client
from ...config import load_config, save_config


class SetupWizardModal(ModalScreen[bool]):
    """Interactive guided setup wizard for initial connection, Google OAuth, and validation."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label("▲ NEXUS INITIAL SETUP WIZARD", classes="modal-header")
            yield Static(
                "Welcome to NEXUS — Personal Digital Infrastructure Ecosystem.\n"
                "Configure your target Core API or hosted Control Plane endpoint.\n",
                id="wizard-intro",
            )
            yield Label("API / Control Plane URL:")
            yield Input(
                value="https://nexus-control-plane-uvi8.onrender.com",
                placeholder="https://nexus-control-plane-uvi8.onrender.com",
                id="wizard-api-url",
            )
            yield Label("\nSession Token (from Google OAuth web login, or leave blank):")
            yield Input(placeholder="eyJhbGciOi...", id="wizard-token", password=True)

            yield Static("", id="wizard-status-msg")

            with Horizontal(classes="modal-footer"):
                yield Button("Test & Save", variant="primary", id="btn-save", classes="modal-button")
                yield Button("Cancel", variant="default", id="btn-cancel", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(False)
            return

        if event.button.id == "btn-save":
            url = self.query_one("#wizard-api-url", Input).value.strip().rstrip("/")
            token = self.query_one("#wizard-token", Input).value.strip() or None

            status_msg = self.query_one("#wizard-status-msg", Static)
            status_msg.update("[cyan]Testing endpoint connectivity...[/cyan]")

            try:
                cfg = load_config()
                cfg.api_url = url
                cfg.control_plane_url = url
                if token:
                    cfg.token = token
                save_config(cfg)

                # Test connection
                client = get_client()
                resp = client.get("/health", timeout=5)
                if resp.status_code == 200:
                    status_msg.update("[green]Connected successfully! Setup complete.[/green]")
                    self.set_timer(1.0, lambda: self.dismiss(True))
                else:
                    status_msg.update(f"[yellow]Endpoint returned HTTP {resp.status_code}. Saved anyway.[/yellow]")
                    self.set_timer(1.5, lambda: self.dismiss(True))
            except Exception as e:
                status_msg.update(f"[red]Connection error: {e}. Config saved.[/red]")
                self.set_timer(2.0, lambda: self.dismiss(True))

    def key_escape(self) -> None:
        self.dismiss(False)
