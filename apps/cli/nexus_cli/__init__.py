"""NEXUS CLI — Power Tools for the NEXUS Ecosystem."""

import warnings

# Suppress LibreSSL vs OpenSSL warning on macOS Python 3.9 environments
warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")
warnings.filterwarnings("ignore", category=Warning, module="urllib3")

__version__ = "0.2.0"
__app_name__ = "nexus"
