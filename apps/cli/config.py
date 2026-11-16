import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

CONFIG_FILE_PATH = Path.home() / ".nexus-cli.json"


class CLIConfig(BaseModel):
    api_url: str = "http://127.0.0.1:8000"
    # Hosted coordination service (Render free tier): login + node registry.
    # Personal data stays on the node — see docs/deploy/online-access.md.
    control_plane_url: Optional[str] = None
    node_id: Optional[int] = None          # this machine's node registration
    node_api_key: Optional[str] = None     # issued once at claim
    token: Optional[str] = None            # access token (control-plane or node)
    refresh_token: Optional[str] = None
    email: Optional[str] = None            # logged-in user (display only)


def load_config() -> CLIConfig:
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return CLIConfig(**data)
        except Exception:
            pass
    return CLIConfig()


def save_config(config: CLIConfig):
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=4)
