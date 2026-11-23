"""Configuration and secure credential management for NEXUS CLI."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

KEYRING_SERVICE = "nexus-cli"
DEFAULT_PUBLIC_URL = "https://nexus-control-plane-uvi8.onrender.com"


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
    def _scoped_key(cls, key: str, profile: Optional[str] = None) -> str:
        if profile and profile != "default":
            return f"{key}_{profile}"
        return key

    @classmethod
    def get_secret(cls, key: str, profile: Optional[str] = None) -> Optional[str]:
        # 1. Environment variable override (highest precedence)
        env_map = {
            "token": "NEXUS_TOKEN",
            "refresh_token": "NEXUS_REFRESH_TOKEN",
            "node_api_key": "NEXUS_NODE_API_KEY",
        }
        if key in env_map and os.environ.get(env_map[key]):
            return os.environ[env_map[key]]

        scoped = cls._scoped_key(key, profile)

        # 2. Keyring lookup
        if cls.is_keyring_enabled():
            try:
                import keyring
                val = keyring.get_password(KEYRING_SERVICE, scoped)
                if val:
                    return val
                if scoped != key:
                    # fallback to unscoped key if scoped doesn't exist
                    val = keyring.get_password(KEYRING_SERVICE, key)
                    if val:
                        return val
            except Exception:
                pass

        # 3. File fallback
        val = cls._read_file_secret(scoped)
        if val is None and scoped != key:
            val = cls._read_file_secret(key)
        return val

    @classmethod
    def set_secret(cls, key: str, value: Optional[str], profile: Optional[str] = None) -> None:
        scoped = cls._scoped_key(key, profile)
        if cls.is_keyring_enabled():
            try:
                import keyring
                if value is None:
                    try:
                        keyring.delete_password(KEYRING_SERVICE, scoped)
                    except Exception:
                        pass
                else:
                    keyring.set_password(KEYRING_SERVICE, scoped, value)
            except Exception:
                pass
        # Always mirror or fallback into mode 0600 config
        cls._write_file_secret(scoped, value)

    @classmethod
    def delete_secret(cls, key: str, profile: Optional[str] = None) -> None:
        cls.set_secret(key, None, profile=profile)

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


class ProfileConfig(BaseModel):
    api_url: str = Field(default=DEFAULT_PUBLIC_URL)
    control_plane_url: Optional[str] = Field(default=DEFAULT_PUBLIC_URL)
    node_id: Optional[int] = None
    email: Optional[str] = None
    timeout: int = 10


class CLIConfig(BaseModel):
    active_profile: str = "default"
    profiles: Dict[str, ProfileConfig] = Field(default_factory=lambda: {"default": ProfileConfig()})
    
    # UI Preferences
    theme: str = "dark"  # dark, synthwave, light
    accent_color: str = "cyan"
    default_view: str = "dashboard"
    favourites: List[str] = Field(default_factory=list)
    recent_commands: List[str] = Field(default_factory=list)

    # Top-level mirror attributes for direct backward compatibility
    api_url: str = Field(default=DEFAULT_PUBLIC_URL)
    control_plane_url: Optional[str] = Field(default=DEFAULT_PUBLIC_URL)
    node_id: Optional[int] = None
    email: Optional[str] = None
    timeout: int = 10

    def current_profile(self) -> ProfileConfig:
        """Resolve current active profile object, initializing if missing."""
        if self.active_profile not in self.profiles:
            self.profiles[self.active_profile] = ProfileConfig(
                api_url=self.api_url,
                control_plane_url=self.control_plane_url,
                node_id=self.node_id,
                email=self.email,
                timeout=self.timeout,
            )
        return self.profiles[self.active_profile]

    def sync_from_active_profile(self) -> None:
        """Mirror current profile values to top-level fields."""
        prof = self.current_profile()
        self.api_url = prof.api_url
        self.control_plane_url = prof.control_plane_url
        self.node_id = prof.node_id
        self.email = prof.email
        self.timeout = prof.timeout

    def sync_to_active_profile(self) -> None:
        """Mirror top-level fields down into current profile."""
        prof = self.current_profile()
        prof.api_url = self.api_url
        prof.control_plane_url = self.control_plane_url
        prof.node_id = self.node_id
        prof.email = self.email
        prof.timeout = self.timeout

    # Accessors for sensitive credentials backed by CredentialStore
    @property
    def token(self) -> Optional[str]:
        return CredentialStore.get_secret("token", profile=self.active_profile)

    @token.setter
    def token(self, val: Optional[str]) -> None:
        CredentialStore.set_secret("token", val, profile=self.active_profile)

    @property
    def refresh_token(self) -> Optional[str]:
        return CredentialStore.get_secret("refresh_token", profile=self.active_profile)

    @refresh_token.setter
    def refresh_token(self, val: Optional[str]) -> None:
        CredentialStore.set_secret("refresh_token", val, profile=self.active_profile)

    @property
    def node_api_key(self) -> Optional[str]:
        return CredentialStore.get_secret("node_api_key", profile=self.active_profile)

    @node_api_key.setter
    def node_api_key(self, val: Optional[str]) -> None:
        CredentialStore.set_secret("node_api_key", val, profile=self.active_profile)

    def record_recent_command(self, cmd_id: str) -> None:
        """Maintain rolling list of most recently executed commands."""
        if cmd_id in self.recent_commands:
            self.recent_commands.remove(cmd_id)
        self.recent_commands.insert(0, cmd_id)
        self.recent_commands = self.recent_commands[:15]

    def toggle_favourite(self, cmd_id: str) -> bool:
        """Toggle a command in favorites list."""
        if cmd_id in self.favourites:
            self.favourites.remove(cmd_id)
            return False
        else:
            self.favourites.append(cmd_id)
            return True


def load_config() -> CLIConfig:
    """Load configuration with precedence: Env vars > JSON file > Defaults."""
    path = get_config_path()
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    # Migrate legacy single-profile structure if needed
    active_prof = data.get("active_profile", "default")
    profiles_raw = data.get("profiles", {})
    if not profiles_raw:
        # Construct default profile from top-level attributes
        default_prof = ProfileConfig(
            api_url=data.get("api_url", os.environ.get("NEXUS_API_URL", DEFAULT_PUBLIC_URL)),
            control_plane_url=data.get(
                "control_plane_url",
                os.environ.get("NEXUS_CONTROL_PLANE_URL", DEFAULT_PUBLIC_URL),
            ),
            node_id=data.get("node_id"),
            email=data.get("email"),
            timeout=int(data.get("timeout", os.environ.get("NEXUS_TIMEOUT", 10))),
        )
        profiles_raw = {"default": default_prof.model_dump()}
    else:
        # Ensure profiles are valid dicts
        for p_name, p_val in profiles_raw.items():
            if isinstance(p_val, dict):
                profiles_raw[p_name] = ProfileConfig(**p_val).model_dump()

    parsed_profiles: Dict[str, ProfileConfig] = {
        k: ProfileConfig(**v) if isinstance(v, dict) else v for k, v in profiles_raw.items()
    }
    if active_prof not in parsed_profiles:
        parsed_profiles[active_prof] = ProfileConfig()

    active_p = parsed_profiles[active_prof]

    # Environment variables take precedence over config file values for active profile
    api_url = os.environ.get("NEXUS_API_URL") or data.get("api_url") or active_p.api_url
    cp_url = os.environ.get("NEXUS_CONTROL_PLANE_URL") or data.get("control_plane_url") or active_p.control_plane_url
    timeout = active_p.timeout
    if os.environ.get("NEXUS_TIMEOUT"):
        try:
            timeout = int(os.environ["NEXUS_TIMEOUT"])
        except ValueError:
            pass
    elif "timeout" in data:
        try:
            timeout = int(data["timeout"])
        except ValueError:
            pass

    node_id = data.get("node_id", active_p.node_id)
    email = data.get("email", active_p.email)

    active_p.api_url = api_url
    active_p.control_plane_url = cp_url
    active_p.timeout = timeout
    active_p.node_id = node_id
    active_p.email = email

    config = CLIConfig(
        active_profile=active_prof,
        profiles=parsed_profiles,
        theme=data.get("theme", "dark"),
        accent_color=data.get("accent_color", "cyan"),
        default_view=data.get("default_view", "dashboard"),
        favourites=data.get("favourites", []),
        recent_commands=data.get("recent_commands", []),
        api_url=api_url,
        control_plane_url=cp_url,
        node_id=node_id,
        email=email,
        timeout=timeout,
    )
    return config


def save_config(config: CLIConfig) -> None:
    """Persist non-sensitive configuration to disk with restricted permissions (0o600)."""
    # Ensure active profile is synchronized
    config.sync_to_active_profile()
    path = get_config_path()
    raw: Dict[str, Any] = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            raw = {}

    # Persist top-level mirror fields for backward compatibility
    raw["api_url"] = config.api_url
    raw["control_plane_url"] = config.control_plane_url
    raw["node_id"] = config.node_id
    raw["email"] = config.email
    raw["timeout"] = config.timeout

    # Persist multi-profile structure
    raw["active_profile"] = config.active_profile
    raw["profiles"] = {k: v.model_dump() for k, v in config.profiles.items()}

    # Persist UI preferences
    raw["theme"] = config.theme
    raw["accent_color"] = config.accent_color
    raw["default_view"] = config.default_view
    raw["favourites"] = config.favourites
    raw["recent_commands"] = config.recent_commands

    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=4)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def reset_config() -> None:
    """Clear all configuration and purge stored credentials across all profiles."""
    path = get_config_path()
    profiles = ["default"]
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                profiles.extend(data.get("profiles", {}).keys())
        except Exception:
            pass

    for prof in set(profiles):
        CredentialStore.delete_secret("token", profile=prof)
        CredentialStore.delete_secret("refresh_token", profile=prof)
        CredentialStore.delete_secret("node_api_key", profile=prof)

    # Legacy unscoped purge
    CredentialStore.delete_secret("token")
    CredentialStore.delete_secret("refresh_token")
    CredentialStore.delete_secret("node_api_key")

    if path.exists():
        path.unlink(missing_ok=True)
