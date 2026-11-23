"""Configuration inspection and management commands with profile support."""

from typing import Optional

import typer

from ..config import CredentialStore, ProfileConfig, load_config, reset_config, save_config
from ..ui import (
    console,
    is_json_mode,
    output_json,
    print_error,
    print_info,
    print_success,
    render_key_value,
    render_table,
    set_json_mode,
)

config_app = typer.Typer(help="Manage CLI configuration, profiles, and environment endpoints")
profile_app = typer.Typer(help="Manage multiple environment and server profiles")
config_app.add_typer(profile_app, name="profile")


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
        "active_profile": cfg.active_profile,
        "api_url": cfg.api_url,
        "control_plane_url": cfg.control_plane_url or "Not configured",
        "email": cfg.email or "Not logged in",
        "node_id": cfg.node_id or "Not registered",
        "timeout": f"{cfg.timeout}s",
        "theme": cfg.theme,
        "token": token_display,
        "node_api_key": key_display,
        "keyring_backend": "OS Keyring (Active)" if CredentialStore.is_keyring_enabled() else "Local Encrypted File",
    }
    if is_json_mode():
        output_json({k: v for k, v in data.items() if not k.startswith("token") and not k.startswith("node_api_key")})
        return

    render_key_value(data, title=f"CLI CONFIGURATION [{cfg.active_profile.upper()}]")


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
        confirm = typer.confirm("This will remove all stored credentials and local settings across all profiles. Continue?")
        if not confirm:
            print_info("Configuration reset aborted.", title="ABORTED")
            return

    reset_config()
    print_success("Configuration file and keychain secrets removed.", title="RESET COMPLETE")


# --- Profile Subcommands ---


@profile_app.command("list")
def profile_list(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List all available environment and server profiles."""
    if json_output:
        set_json_mode(True)
    cfg = load_config()

    rows = []
    for name, prof in cfg.profiles.items():
        is_active = (name == cfg.active_profile)
        rows.append({
            "name": name,
            "active": is_active,
            "api_url": prof.api_url,
            "email": prof.email or "None",
            "node_id": str(prof.node_id) if prof.node_id else "None",
        })

    if is_json_mode():
        output_json({"active_profile": cfg.active_profile, "profiles": rows})
        return

    render_table(
        rows=[
            [
                f"[bold green]* {r['name']}[/bold green]" if r["active"] else f"  {r['name']}",
                r["api_url"],
                r["email"],
                r["node_id"],
            ]
            for r in rows
        ],
        headers=["Profile", "API URL", "Email", "Node ID"],
        title="NEXUS PROFILES",
    )


@profile_app.command("switch")
def profile_switch(
    name: str = typer.Argument(..., help="Name of profile to activate"),
):
    """Switch active configuration profile."""
    cfg = load_config()
    if name not in cfg.profiles:
        print_error(f"Profile '{name}' does not exist. Create it first using 'nexus config profile create {name}'.", title="PROFILE ERROR")
        raise typer.Exit(1)

    cfg.active_profile = name
    cfg.sync_from_active_profile()
    save_config(cfg)
    print_success(f"Switched active profile to [bold cyan]{name}[/bold cyan] ({cfg.api_url})", title="PROFILE SWITCHED")


@profile_app.command("create")
def profile_create(
    name: str = typer.Argument(..., help="Name of new profile"),
    api_url: str = typer.Option("https://nexus-control-plane-uvi8.onrender.com", "--url", "-u", help="API base URL"),
    control_plane_url: Optional[str] = typer.Option(None, "--cp", help="Control plane URL"),
    activate: bool = typer.Option(True, "--activate/--no-activate", help="Activate profile immediately"),
):
    """Create a new profile."""
    cfg = load_config()
    if name in cfg.profiles:
        print_error(f"Profile '{name}' already exists.", title="PROFILE ERROR")
        raise typer.Exit(1)

    cp = control_plane_url or api_url
    cfg.profiles[name] = ProfileConfig(
        api_url=api_url.rstrip("/"),
        control_plane_url=cp.rstrip("/"),
        timeout=10,
    )
    if activate:
        cfg.active_profile = name
        cfg.sync_from_active_profile()

    save_config(cfg)
    msg = f"Created profile [bold cyan]{name}[/bold cyan] pointing to [bold]{api_url}[/bold]."
    if activate:
        msg += " Set as active profile."
    print_success(msg, title="PROFILE CREATED")


@profile_app.command("delete")
def profile_delete(
    name: str = typer.Argument(..., help="Name of profile to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a profile and its stored credentials."""
    cfg = load_config()
    if name == "default":
        print_error("Cannot delete the default profile.", title="PROFILE ERROR")
        raise typer.Exit(1)
    if name not in cfg.profiles:
        print_error(f"Profile '{name}' not found.", title="PROFILE ERROR")
        raise typer.Exit(1)

    if not yes:
        confirm = typer.confirm(f"Are you sure you want to delete profile '{name}' and its credentials?")
        if not confirm:
            print_info("Profile deletion aborted.", title="ABORTED")
            return

    # Delete profile secrets
    CredentialStore.delete_secret("token", profile=name)
    CredentialStore.delete_secret("refresh_token", profile=name)
    CredentialStore.delete_secret("node_api_key", profile=name)

    del cfg.profiles[name]
    if cfg.active_profile == name:
        cfg.active_profile = "default"
        cfg.sync_from_active_profile()

    save_config(cfg)
    print_success(f"Deleted profile [bold cyan]{name}[/bold cyan]. Active profile is now [bold]{cfg.active_profile}[/bold].", title="PROFILE DELETED")
