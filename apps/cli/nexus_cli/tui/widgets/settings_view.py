"""Settings and Personalization Widget for NEXUS Control Center."""

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, DataTable, Input, Label, Static, Switch

from ...config import CredentialStore, load_config, save_config
from .context import ContextPanel


class SettingsView(Static):
    """Personalization and Configuration View for themes, profiles, startup view, and privacy."""

    class SettingsChanged(Message):
        def __init__(self, key: str, value: Any) -> None:
            self.key = key
            self.value = value
            super().__init__()

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="settings-scroll-container"):
            with Horizontal(classes="view-header-bar"):
                yield Label("🛠️ SETTINGS & PROFILE PREFERENCES", classes="view-title")
                with Horizontal(classes="header-actions"):
                    yield Button("💾 Save Settings", id="btn-save-settings", variant="primary", classes="btn-sm")

            # Appearance Box
            with Vertical(classes="overview-full-card", id="box-appearance"):
                yield Label("🎨 APPEARANCE & THEMES", classes="card-header")
                yield Label("Color Theme Selection:")
                with Horizontal(classes="btn-group-row"):
                    yield Button("Dark (Default)", id="theme-dark", classes="btn-sm")
                    yield Button("Synthwave", id="theme-synthwave", classes="btn-sm")
                    yield Button("Light", id="theme-light", classes="btn-sm")

                with Horizontal(classes="config-bar"):
                    yield Label("Compact Layout Mode:")
                    yield Switch(id="switch-compact-mode")

            # Interface & Privacy Box
            with Vertical(classes="overview-full-card", id="box-privacy-interface"):
                yield Label("🔒 PRIVACY & INTERFACE", classes="card-header")
                with Horizontal(classes="config-bar"):
                    yield Label("Mask Email Addresses in Dashboard / Headers:")
                    yield Switch(id="switch-privacy-email")

                yield Label("\nDefault Startup View:")
                with Horizontal(classes="btn-group-row"):
                    yield Button("Overview", id="startup-overview", classes="btn-sm")
                    yield Button("Devices", id="startup-devices", classes="btn-sm")
                    yield Button("Files", id="startup-files", classes="btn-sm")
                    yield Button("Tasks", id="startup-tasks", classes="btn-sm")
                    yield Button("Doctor", id="startup-doctor", classes="btn-sm")

            # Profile Manager Box
            with Vertical(classes="overview-full-card", id="box-profiles"):
                yield Label("👤 PROFILE MANAGEMENT", classes="card-header")
                yield Label("Active Profiles (Select row to switch active profile):")
                table = DataTable(id="profiles-table", cursor_type="row")
                table.zebra_stripes = True
                yield table

                yield Label("\nCreate New Profile:")
                with Horizontal(classes="form-inline-row"):
                    yield Input(placeholder="Profile Name (e.g. personal, dev)", id="new-profile-name")
                    yield Input(placeholder="Control Plane URL", id="new-profile-url")
                    yield Button("➕ Create Profile", id="btn-create-profile", variant="primary", classes="btn-sm")

            # Security & Credential Store Box
            with Vertical(classes="overview-full-card", id="box-security-store"):
                yield Label("🛡️ CREDENTIAL STORE & STORAGE STATUS", classes="card-header")
                yield Static("Loading credential store info...", id="security-store-static")

            # Keyboard Shortcuts Reference Sheet
            with Vertical(classes="overview-full-card", id="box-shortcuts"):
                yield Label("⌨️ KEYBOARD SHORTCUTS & HOTKEYS", classes="card-header")
                shortcuts_text = (
                    "• [bold cyan]/[/bold cyan] or [bold cyan]Ctrl+K[/bold cyan] : Global Command Palette (Fuzzy search)\n"
                    "• [bold cyan]1 - 9[/bold cyan]          : Quick Jump between Workspace Views\n"
                    "• [bold cyan]r[/bold cyan]              : Refresh Active View & Telemetry\n"
                    "• [bold cyan]?[/bold cyan]              : Help & Documentation Sheet\n"
                    "• [bold cyan]p[/bold cyan]              : Quick Profile Switcher\n"
                    "• [bold cyan]w[/bold cyan]              : Setup Wizard (First-Run)\n"
                    "• [bold cyan]q[/bold cyan]              : Quit NEXUS TUI Control Center\n"
                )
                yield Static(shortcuts_text, id="shortcuts-static")

    def on_mount(self) -> None:
        table = self.query_one("#profiles-table", DataTable)
        table.add_columns("Active", "Profile Name", "Endpoint URL")
        self.refresh_settings_view()

    def refresh_settings_view(self) -> None:
        cfg = load_config()

        # Update switches
        sw_priv = self.query_one("#switch-privacy-email", Switch)
        sw_priv.value = cfg.mask_email

        sw_comp = self.query_one("#switch-compact-mode", Switch)
        sw_comp.value = cfg.compact_mode

        # Update profiles table
        table = self.query_one("#profiles-table", DataTable)
        table.clear()
        for p_name, p_conf in cfg.profiles.items():
            is_active = (p_name == cfg.active_profile)
            marker = "[bold green]★ ACTIVE[/bold green]" if is_active else "[dim]STANDBY[/dim]"
            table.add_row(marker, f"[bold cyan]{p_name}[/bold cyan]", p_conf.api_url, key=p_name)

        # Update security store static
        keyring_active = CredentialStore.is_keyring_enabled()
        backend_name = "OS Keychain / Secret Service" if keyring_active else "None"
        store_lines = [
            f"[bold cyan]Credential Vault:[/bold cyan] {'[green]● Secure OS Keyring Active[/green]' if keyring_active else '[yellow]⚠️ File Fallback (0600 permissions)[/yellow]'}",
            f"[bold cyan]Storage Backend:[/bold cyan] {backend_name}",
            f"[bold cyan]Active Token Isolation:[/bold cyan] Per-profile credential scoping enabled.",
            f"[bold cyan]TLS Enforcement:[/bold cyan] HTTPS / WSS Strictly Verified.",
        ]
        self.query_one("#security-store-static", Static).update("\n".join(store_lines))

        # Update Context Panel
        try:
            ctx = self.app.query_one(ContextPanel)
            ctx.update_resource(
                title="Settings & Preferences",
                subtitle=f"Profile: {cfg.active_profile}",
                properties={
                    "Theme": cfg.theme,
                    "Mask Email": "Yes" if cfg.mask_email else "No",
                    "Compact Mode": "Yes" if cfg.compact_mode else "No",
                    "Active Profile": cfg.active_profile,
                },
                action_label="Save Preferences",
                action_id="settings.save",
                help_text="Customizes appearance, privacy masking, and active multi-profile routing.",
            )
        except Exception:
            pass

    def on_switch_changed(self, event: Switch.Changed) -> None:
        cfg = load_config()
        if event.switch.id == "switch-privacy-email":
            cfg.mask_email = event.value
            save_config(cfg)
            self.post_message(self.SettingsChanged("mask_email", event.value))
        elif event.switch.id == "switch-compact-mode":
            cfg.compact_mode = event.value
            save_config(cfg)
            self.post_message(self.SettingsChanged("compact_mode", event.value))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value:
            cfg = load_config()
            cfg.active_profile = event.row_key.value
            cfg.sync_from_active_profile()
            save_config(cfg)
            self.refresh_settings_view()
            self.post_message(self.SettingsChanged("active_profile", event.row_key.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        cfg = load_config()
        btn_id = event.button.id

        if btn_id == "theme-dark":
            cfg.theme = "dark"
            save_config(cfg)
            self.post_message(self.SettingsChanged("theme", "dark"))
        elif btn_id == "theme-synthwave":
            cfg.theme = "synthwave"
            save_config(cfg)
            self.post_message(self.SettingsChanged("theme", "synthwave"))
        elif btn_id == "theme-light":
            cfg.theme = "light"
            save_config(cfg)
            self.post_message(self.SettingsChanged("theme", "light"))
        elif btn_id == "startup-overview":
            cfg.default_view = "overview"
            save_config(cfg)
        elif btn_id == "startup-devices":
            cfg.default_view = "devices"
            save_config(cfg)
        elif btn_id == "startup-files":
            cfg.default_view = "files"
            save_config(cfg)
        elif btn_id == "startup-tasks":
            cfg.default_view = "tasks"
            save_config(cfg)
        elif btn_id == "startup-doctor":
            cfg.default_view = "doctor"
            save_config(cfg)
        elif btn_id == "btn-save-settings":
            save_config(cfg)
            self.app.notify("Preferences successfully saved.", title="Settings", severity="information")
        elif btn_id == "btn-create-profile":
            p_name = self.query_one("#new-profile-name", Input).value.strip()
            p_url = self.query_one("#new-profile-url", Input).value.strip() or cfg.api_url
            if p_name:
                from ...config import ProfileConfig
                cfg.profiles[p_name] = ProfileConfig(api_url=p_url)
                save_config(cfg)
                self.query_one("#new-profile-name", Input).value = ""
                self.query_one("#new-profile-url", Input).value = ""
                self.refresh_settings_view()
                self.app.notify(f"Profile '{p_name}' created.", title="Profiles", severity="information")

