"""Backward-compatibility shim for apps/cli/config.py."""

from nexus_cli.config import (
    CONFIG_FILE_PATH,
    CLIConfig,
    CredentialStore,
    get_config_path,
    load_config,
    reset_config,
    save_config,
)

__all__ = [
    "CONFIG_FILE_PATH",
    "CLIConfig",
    "CredentialStore",
    "get_config_path",
    "load_config",
    "save_config",
    "reset_config",
]
