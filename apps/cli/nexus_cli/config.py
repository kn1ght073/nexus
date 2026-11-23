"""Configuration and secure credential management for NEXUS CLI."""

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

KEYRING_SERVICE = "nexus-cli"


def get_config_path() -> Path:
    """Resolve active configuration path respecting runtime environment overrides."""
    return Path(os.environ.get("NEXUS_CLI_CONFIG", Path.home() / ".nexus-cli.json"))


# Backward-compatible global reference
CONFIG_FILE_PATH = get_config_path()


class CredentialStore:
    """Secure credential storage utilizing OS Keyring with graceful mode 0600 file fallback."""

    @classmethod
    def is_keyring_enabled(cls) -> bool:
        if os.environ.get("NEXUS_DISABLE_KEYRING", "").lower() in ("1", "true", "yes"):
            return False
        try:
            import keyring
            backend = keyring.get_keyring()
            if "fail" in backend.__class__.__name__.lower() or "null" in backend.__class__.__name__.lower():
                return False
            return True
        except Exception:
            return False

    @classmethod
    def get_secret(cls, key: str) -> Optional[str]:
        # 1. Environment variable override
        env_map = {
            "token": "NEXUS_TOKEN",
            "refresh_token": "NEXUS_REFRESH_TOKEN",
            "node_api_key": "NEXUS_NODE_API_KEY",
        }
        if key in env_map and os.environ.get(env_map[key]):
            return os.environ[env_map[key]]

        # 2. Keyring lookup
        if cls.is_keyring_enabled():
            try:
                import keyring
                val = keyring.get_password(KEYRING_SERVICE, key)
                if val:
                    return val
            except Exception:
                pass

        # 3. File fallback
        return cls._read_file_secret(key)

    @classmethod
    def set_secret(cls, key: str, value: Optional[str]) -> None:
        if cls.is_keyring_enabled():
            try:
                import keyring
                if value is None:
                    try:
                        keyring.delete_password(KEYRING_SERVICE, key)
                    except Exception:
                        pass
                else:
                    keyring.set_password(KEYRING_SERVICE, key, value)
            except Exception:
                pass
        # Always mirror or fallback into mode 0600 config
        cls._write_file_secret(key, value)

    @classmethod
    def delete_secret(cls, key: str) -> None:
        cls.set_secret(key, None)

    @classmethod
    def _read_file_secret(cls, key: str) -> Optional[str]:
        path = get_config_path()
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(key)
        except Exception:
            return None

    @classmethod
    def _write_file_secret(cls, key: str, value: Optional[str]) -> None:
        path = get_config_path()
        data = {}
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


class CLIConfig(BaseModel):
    api_url: str = Field(
        default_factory=lambda: os.environ.get("NEXUS_API_URL", "http://127.0.0.1:8000")
    )
    control_plane_url: Optional[str] = Field(
        default_factory=lambda: os.environ.get(
            "NEXUS_PUBLIC_URL",
            os.environ.get("NEXUS_CONTROL_PLANE_URL", "https://nexus-control-plane-uvi8.onrender.com"),
        )
    )
    node_id: Optional[int] = None
    email: Optional[str] = None
    timeout: int = Field(default_factory=lambda: int(os.environ.get("NEXUS_TIMEOUT", "10")))

    # Accessors for sensitive credentials backed by CredentialStore
    @property
    def token(self) -> Optional[str]:
        return CredentialStore.get_secret("token")

    @token.setter
    def token(self, val: Optional[str]) -> None:
        CredentialStore.set_secret("token", val)

    @property
    def refresh_token(self) -> Optional[str]:
        return CredentialStore.get_secret("refresh_token")

    @refresh_token.setter
    def refresh_token(self, val: Optional[str]) -> None:
        CredentialStore.set_secret("refresh_token", val)

    @property
    def node_api_key(self) -> Optional[str]:
        return CredentialStore.get_secret("node_api_key")

    @node_api_key.setter
    def node_api_key(self, val: Optional[str]) -> None:
        CredentialStore.set_secret("node_api_key", val)


def load_config() -> CLIConfig:
    """Load configuration with precedence: Env vars > JSON file > Defaults."""
    path = get_config_path()
    data = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    # Environment variables take precedence over config file values
    if os.environ.get("NEXUS_API_URL"):
        data["api_url"] = os.environ["NEXUS_API_URL"]
    if os.environ.get("NEXUS_CONTROL_PLANE_URL"):
        data["control_plane_url"] = os.environ["NEXUS_CONTROL_PLANE_URL"]
    if os.environ.get("NEXUS_TIMEOUT"):
        try:
            data["timeout"] = int(os.environ["NEXUS_TIMEOUT"])
        except ValueError:
            pass

    return CLIConfig(**data)


def save_config(config: CLIConfig) -> None:
    """Persist non-sensitive configuration to disk with restricted permissions."""
    path = get_config_path()
    raw = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            raw = {}

    # Update non-credential fields
    raw["api_url"] = config.api_url
    raw["control_plane_url"] = config.control_plane_url
    raw["node_id"] = config.node_id
    raw["email"] = config.email
    raw["timeout"] = config.timeout

    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=4)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def reset_config() -> None:
    """Clear all configuration and purge stored credentials."""
    CredentialStore.delete_secret("token")
    CredentialStore.delete_secret("refresh_token")
    CredentialStore.delete_secret("node_api_key")
    path = get_config_path()
    if path.exists():
        path.unlink(missing_ok=True)
