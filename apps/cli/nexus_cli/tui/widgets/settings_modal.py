"""Settings Modal for theme, profile switching, and endpoint preferences."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from ...config import load_config, save_config


class SettingsModal(ModalScreen[bool]):
    """Modal dialog for customizing local TUI preferences, themes, and profiles."""

    def compose(self) -> ComposeResult:
        cfg = load_config()
        with Vertical(classes="modal-box"):
            yield Label("TUI PREFERENCES & PROFILE SETTINGS", classes="modal-header")
            yield Label("Active Profile:")
            opt_list = OptionList(id="settings-profile-list")
            for p_name in cfg.profiles.keys():
                is_active = (p_name == cfg.active_profile)
                line = f"{'* ' if is_active else '  '}{p_name} ({cfg.profiles[p_name].api_url})"
                opt_list.add_option(Option(line, id=p_name))
            yield opt_list

            yield Label("\nTheme selection:")
            with Horizontal(classes="modal-footer"):
                yield Button("Dark (Default)", variant="primary", id="theme-dark", classes="modal-button")
                yield Button("Synthwave", variant="warning", id="theme-synthwave", classes="modal-button")
                yield Button("Light", variant="default", id="theme-light", classes="modal-button")

            with Horizontal(classes="modal-footer"):
                yield Button("Close (Esc)", variant="default", id="btn-close", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        cfg = load_config()
        if event.button.id == "btn-close":
            self.dismiss(False)
        elif event.button.id == "theme-dark":
            cfg.theme = "dark"
            save_config(cfg)
            self.dismiss(True)
        elif event.button.id == "theme-synthwave":
            cfg.theme = "synthwave"
            save_config(cfg)
            self.dismiss(True)
        elif event.button.id == "theme-light":
            cfg.theme = "light"
            save_config(cfg)
            self.dismiss(True)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_id:
            cfg = load_config()
            cfg.active_profile = event.option_id
            cfg.sync_from_active_profile()
            save_config(cfg)
            self.dismiss(True)

    def key_escape(self) -> None:
        self.dismiss(False)
