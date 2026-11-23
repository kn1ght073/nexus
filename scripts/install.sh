#!/usr/bin/env bash
set -e

# Resolve repository directory
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${HOME}/.nexus-venv"
BIN_DIR="${HOME}/.local/bin"

echo "==> Installing NEXUS CLI..."

# 1. Resolve installer (prefer uv for speed, fallback to python3 venv)
if command -v uv >/dev/null 2>&1; then
    INSTALLER="uv"
elif command -v python3 >/dev/null 2>&1; then
    INSTALLER="python3"
else
    echo "Error: Python 3.11+ or uv is required." >&2
    exit 1
fi

# 2. Create or reuse managed venv
if [ ! -d "$VENV_DIR" ]; then
    echo "==> Creating managed venv at $VENV_DIR..."
    if [ "$INSTALLER" = "uv" ]; then
        uv venv "$VENV_DIR" --python 3.11 2>/dev/null || uv venv "$VENV_DIR"
    else
        python3 -m venv "$VENV_DIR"
    fi
fi

# 3. Install core and CLI in editable mode
echo "==> Installing packages in editable mode..."
if [ "$INSTALLER" = "uv" ]; then
    uv pip install -e "$REPO_DIR/apps/cli" -e "$REPO_DIR/services/core-api" --python "$VENV_DIR/bin/python"
else
    "$VENV_DIR/bin/python" -m pip install --upgrade pip
    "$VENV_DIR/bin/python" -m pip install -e "$REPO_DIR/apps/cli" -e "$REPO_DIR/services/core-api"
fi

# 4. Link binary to ~/.local/bin
mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/nexus" "$BIN_DIR/nexus"

# 5. Check PATH
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo "Notice: $BIN_DIR is not in your \$PATH."
        echo "Add this to your shell config (~/.zshrc or ~/.bashrc):"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        ;;
esac

echo "==> Verification:"
"$BIN_DIR/nexus" --help >/dev/null && echo "==> NEXUS installed successfully. Type 'nexus' to get started."
