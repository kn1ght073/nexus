"""Unit tests for multi-profile configuration and credential isolation."""

import json
import pytest
from typer.testing import CliRunner

from nexus_cli.cli import app
from nexus_cli.config import CredentialStore, load_config, save_config

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    cfg_file = tmp_path / "profiles_test_config.json"
    monkeypatch.setenv("NEXUS_CLI_CONFIG", str(cfg_file))
    monkeypatch.setenv("NEXUS_DISABLE_KEYRING", "1")
    monkeypatch.delenv("NEXUS_TOKEN", raising=False)
    monkeypatch.delenv("NEXUS_API_URL", raising=False)
    monkeypatch.delenv("NEXUS_CONTROL_PLANE_URL", raising=False)
    yield cfg_file


def test_default_profile_initialization():
    cfg = load_config()
    assert cfg.active_profile == "default"
    assert "default" in cfg.profiles
    assert cfg.api_url == cfg.profiles["default"].api_url


def test_profile_cli_create_and_switch():
    # Create profile
    res = runner.invoke(app, ["config", "profile", "create", "staging", "--url", "https://staging.nexus.local"])
    assert res.exit_code == 0
    assert "Created profile staging" in res.stdout

    cfg = load_config()
    assert "staging" in cfg.profiles
    assert cfg.active_profile == "staging"
    assert cfg.api_url == "https://staging.nexus.local"

    # Switch back to default
    switch_res = runner.invoke(app, ["config", "profile", "switch", "default"])
    assert switch_res.exit_code == 0
    assert "Switched active profile to default" in switch_res.stdout

    cfg_reloaded = load_config()
    assert cfg_reloaded.active_profile == "default"


def test_profile_credential_isolation():
    cfg = load_config()
    cfg.active_profile = "default"
    cfg.token = "token-for-default"

    # Switch to staging
    cfg.profiles["staging"] = cfg.profiles["default"].model_copy()
    cfg.active_profile = "staging"
    cfg.token = "token-for-staging"

    # Verify staging token
    assert cfg.token == "token-for-staging"

    # Switch back to default and verify
    cfg.active_profile = "default"
    assert cfg.token == "token-for-default"


def test_profile_list_json():
    runner.invoke(app, ["config", "profile", "create", "prod", "--url", "https://prod.nexus.local"])
    res = runner.invoke(app, ["config", "profile", "list", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["active_profile"] == "prod"
    profile_names = [p["name"] for p in data["profiles"]]
    assert "default" in profile_names
    assert "prod" in profile_names


def test_profile_delete_protection():
    # Attempting to delete default profile must fail
    res = runner.invoke(app, ["config", "profile", "delete", "default", "--yes"])
    assert res.exit_code != 0
    assert "Cannot delete the default profile" in (res.stderr or res.stdout)

    # Create and delete a custom profile
    runner.invoke(app, ["config", "profile", "create", "temp", "--url", "http://temp.local"])
    del_res = runner.invoke(app, ["config", "profile", "delete", "temp", "--yes"])
    assert del_res.exit_code == 0
    assert "Deleted profile temp" in del_res.stdout
