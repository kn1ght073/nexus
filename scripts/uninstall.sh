#!/usr/bin/env bash
set -e

VENV_DIR="${HOME}/.nexus-venv"
BIN_DIR="${HOME}/.local/bin"
CONFIG_FILE="${HOME}/.nexus-cli.json"

echo "==> Uninstalling NEXUS..."
rm -f "$BIN_DIR/nexus"
rm -rf "$VENV_DIR"

if [ "$1" = "--purge" ]; then
    rm -f "$CONFIG_FILE"
    echo "==> Removed configuration and credentials ($CONFIG_FILE)."
fi

echo "==> NEXUS uninstalled successfully."
