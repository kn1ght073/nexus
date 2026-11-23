"""NEXUS CLI — Primary Entrypoint and Backward-Compatibility Shim."""

import sys
import warnings
from pathlib import Path

# Suppress LibreSSL vs OpenSSL warning on macOS Python 3.9 environments
warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")
warnings.filterwarnings("ignore", category=Warning, module="urllib3")

# Ensure package directory is on sys.path regardless of execution context or old venvs
_cli_dir = str(Path(__file__).resolve().parent)
if _cli_dir not in sys.path:
    sys.path.insert(0, _cli_dir)

from nexus_cli.cli import app

if __name__ == "__main__":
    app()
