"""Configuration inspection and management commands."""

import typer

from ..config import CredentialStore, load_config, reset_config, save_config
from ..ui import (
    console,
    is_json_mode,
    output_json,
    print_error,
    print_info,
    print_success,
    render_key_value,
    set_json_mode,
)

config_app = typer.Typer(help="Manage CLI configuration and environment endpoints")


@config_app.command("list")
def config_list(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List active configuration parameters with secret redaction."""
    if json_output:
        set_json_mode(True)
    cfg = load_config()
    token = cfg.token
    token_display = f"*** ({len(token)} chars)" if token else "[dim]None[/dim]"
    key_display = f"*** ({len(cfg.node_api_key)} chars)" if cfg.node_api_key else "[dim]None[/dim]"

    data = {
        "api_url": cfg.api_url,
        "control_plane_url": cfg.control_plane_url or "Not configured",
        "email": cfg.email or "Not logged in",
        "node_id": cfg.node_id or "Not registered",
        "timeout": f"{cfg.timeout}s",
        "token": token_display,
        "node_api_key": key_display,
        "keyring_backend": "OS Keyring (Active)" if CredentialStore.is_keyring_enabled() else "Local Encrypted File",
    }
    if is_json_mode():
        output_json({k: v for k, v in data.items() if not k.startswith("token") and not k.startswith("node_api_key")})
        return

    render_key_value(data, title="CLI CONFIGURATION")


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Configuration key to retrieve"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Get a single configuration value."""
    if json_output:
        set_json_mode(True)
    cfg = load_config()
    val = getattr(cfg, key, None)
    if key in ("token", "refresh_token", "node_api_key"):
        val = "***" if val else None

    if is_json_mode():
        output_json({key: val})
        return
    console.print(f"[bold cyan]{key}[/bold cyan] = {val}")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration parameter name"),
    value: str = typer.Argument(..., help="New value to persist"),
):
    """Set a single configuration value."""
    cfg = load_config()
    if not hasattr(cfg, key):
        print_error(f"Unknown configuration key '{key}'.", title="CONFIG ERROR")
        return

    if key == "timeout":
        try:
            cfg.timeout = int(value)
        except ValueError:
            print_error("Timeout must be a valid integer number of seconds.", title="CONFIG ERROR")
            return
    elif key == "node_id":
        try:
            cfg.node_id = int(value) if value.lower() != "none" else None
        except ValueError:
            print_error("Node ID must be an integer.", title="CONFIG ERROR")
            return
    else:
        setattr(cfg, key, value)

    save_config(cfg)
    print_success(f"Updated [bold cyan]{key}[/bold cyan] to [bold]{value}[/bold].", title="CONFIG UPDATED")


@config_app.command("reset")
def config_reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Purge local configuration file and all stored credentials."""
    if not yes:
        confirm = typer.confirm("This will remove all stored credentials and local settings. Continue?")
        if not confirm:
            print_info("Configuration reset aborted.", title="ABORTED")
            return

    reset_config()
    print_success("Configuration file and keychain secrets removed.", title="RESET COMPLETE")
