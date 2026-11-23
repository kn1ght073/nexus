"""Legacy and standalone entry point for NEXUS Full-Screen TUI."""

import sys
from pathlib import Path

# Ensure package root is in sys.path
_cli_root = Path(__file__).resolve().parent
if str(_cli_root) not in sys.path:
    sys.path.insert(0, str(_cli_root))

from nexus_cli.tui.app import NexusTUI, NexusTUIApp

if __name__ == "__main__":
    app = NexusTUIApp()
    app.run()
