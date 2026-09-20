import os
import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

CONFIG_FILE_PATH = Path.home() / ".nexus-cli.json"

class CLIConfig(BaseModel):
    api_url: str = "http://127.0.0.1:8000"
    token: Optional[str] = None

def load_config() -> CLIConfig:
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, "r") as f:
                data = json.load(f)
                return CLIConfig(**data)
        except Exception:
            pass
    return CLIConfig()

def save_config(config: CLIConfig):
    with open(CONFIG_FILE_PATH, "w") as f:
        json.dump(config.model_dump(), f, indent=4)
