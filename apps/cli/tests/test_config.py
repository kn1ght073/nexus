"""Unit tests for configuration and credential management."""

import os
import stat
from pathlib import Path

import pytest

from nexus_cli.config import (
    CLIConfig,
    CredentialStore,
    get_config_path,
    load_config,
    reset_config,
    save_config,
)


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Ensure every test uses a clean temporary config file and disables OS keyring prompts."""
    cfg_file = tmp_path / "test_config.json"
    monkeypatch.setenv("NEXUS_CLI_CONFIG", str(cfg_file))
    monkeypatch.setenv("NEXUS_DISABLE_KEYRING", "1")
    monkeypatch.delenv("NEXUS_API_URL", raising=False)
    monkeypatch.delenv("NEXUS_CONTROL_PLANE_URL", raising=False)
    monkeypatch.delenv("NEXUS_TOKEN", raising=False)
    monkeypatch.delenv("NEXUS_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("NEXUS_NODE_API_KEY", raising=False)
    yield cfg_file


def test_default_config():
    cfg = load_config()
    assert cfg.api_url == "https://nexus-control-plane-uvi8.onrender.com"
    assert "render.com" in cfg.control_plane_url
    assert cfg.node_id is None
    assert cfg.token is None


def test_save_and_load_config(isolated_config):
    cfg = load_config()
    cfg.api_url = "http://localhost:9999"
    cfg.email = "operator@nexus.test"
    cfg.node_id = 42
    save_config(cfg)

    loaded = load_config()
    assert loaded.api_url == "http://localhost:9999"
    assert loaded.email == "operator@nexus.test"
    assert loaded.node_id == 42


def test_config_file_permissions(isolated_config):
    cfg = load_config()
    save_config(cfg)

    mode = stat.S_IMODE(isolated_config.stat().st_mode)
    assert mode == 0o600


def test_credentials_storage_and_purging(isolated_config):
    cfg = load_config()
    cfg.token = "secret-access-token"
    cfg.refresh_token = "secret-refresh-token"
    cfg.node_api_key = "secret-node-key"

    # Verify retrieval
    assert cfg.token == "secret-access-token"
    assert cfg.refresh_token == "secret-refresh-token"
    assert cfg.node_api_key == "secret-node-key"

    # Reset configuration
    reset_config()
    reloaded = load_config()
    assert reloaded.token is None
    assert reloaded.refresh_token is None
    assert reloaded.node_api_key is None


def test_environment_variable_precedence(isolated_config, monkeypatch):
    cfg = load_config()
    cfg.api_url = "http://from-file:8000"
    save_config(cfg)

    monkeypatch.setenv("NEXUS_API_URL", "http://from-env:9000")
    monkeypatch.setenv("NEXUS_TOKEN", "env-injected-token")

    loaded = load_config()
    assert loaded.api_url == "http://from-env:9000"
    assert loaded.token == "env-injected-token"
