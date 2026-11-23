"""Unit tests for CLI commands and subcommands via Typer CliRunner."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from nexus_cli.cli import app
from nexus_cli import __version__

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_cli(tmp_path, monkeypatch):
    cfg_file = tmp_path / "cli_test_config.json"
    monkeypatch.setenv("NEXUS_CLI_CONFIG", str(cfg_file))
    monkeypatch.setenv("NEXUS_DISABLE_KEYRING", "1")


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout

    json_result = runner.invoke(app, ["version", "--json"])
    assert json_result.exit_code == 0
    data = json.loads(json_result.stdout)
    assert data["version"] == __version__


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "NEXUS CLI" in result.stdout
    assert "doctor" in result.stdout
    assert "auth" in result.stdout
    assert "devices" in result.stdout
    assert "nodes" in result.stdout


def test_cli_init_command():
    result = runner.invoke(app, ["init", "--url", "http://127.0.0.1:8989"])
    assert result.exit_code == 0
    assert "http://127.0.0.1:8989" in result.stdout


def test_doctor_command_json():
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "status" in data
    assert "checks" in data
    assert any(c["name"] == "CLI Version" for c in data["checks"])


def test_auth_status_json():
    result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "authenticated" in data
    assert "api_url" in data


def test_config_commands():
    # Set config value
    set_res = runner.invoke(app, ["config", "set", "api_url", "http://test-server:5000"])
    assert set_res.exit_code == 0

    # Get config value
    get_res = runner.invoke(app, ["config", "get", "api_url"])
    assert get_res.exit_code == 0
    assert "http://test-server:5000" in get_res.stdout

    # List config JSON
    list_res = runner.invoke(app, ["config", "list", "--json"])
    assert list_res.exit_code == 0
    cfg = json.loads(list_res.stdout)
    assert cfg["api_url"] == "http://test-server:5000"


@patch("requests.Session.request")
def test_devices_list_json(mock_req):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": 1, "name": "MacBook", "platform": "macos", "is_online": True}]
    mock_req.return_value = mock_resp

    res = runner.invoke(app, ["devices", "list", "--json"])
    assert res.exit_code == 0
    devs = json.loads(res.stdout)
    assert len(devs) == 1
    assert devs[0]["name"] == "MacBook"


@patch("requests.Session.request")
def test_nodes_list_json(mock_req):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": 10, "name": "Workstation", "platform": "linux", "is_active": True}]
    mock_req.return_value = mock_resp

    res = runner.invoke(app, ["nodes", "list", "--json"])
    assert res.exit_code == 0
    nodes = json.loads(res.stdout)
    assert len(nodes) == 1
    assert nodes[0]["id"] == 10


@patch("requests.Session.request")
def test_projects_list_json(mock_req):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": 1, "title": "Infrastructure Modernization", "status": "active"}]
    mock_req.return_value = mock_resp

    res = runner.invoke(app, ["projects", "list", "--json"])
    assert res.exit_code == 0
    projs = json.loads(res.stdout)
    assert projs[0]["title"] == "Infrastructure Modernization"


@patch("requests.Session.request")
def test_tasks_list_json(mock_req):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": 5, "title": "Audit kernel drivers", "status": "pending"}]
    mock_req.return_value = mock_resp

    res = runner.invoke(app, ["tasks", "list", "--json"])
    assert res.exit_code == 0
    tasks = json.loads(res.stdout)
    assert tasks[0]["id"] == 5


@patch("requests.Session.request")
def test_notes_list_json(mock_req):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": 2, "title": "Syscall stubs", "content": "direct syscalls table"}]
    mock_req.return_value = mock_resp

    res = runner.invoke(app, ["notes", "list", "--json"])
    assert res.exit_code == 0
    notes = json.loads(res.stdout)
    assert notes[0]["title"] == "Syscall stubs"


@patch("requests.Session.request")
def test_account_overview_json(mock_req):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "account_id": "acc-123",
        "email": "user@example.com",
        "role": "user",
        "is_active": True,
        "devices": {"total": 2, "active": 1},
    }
    mock_req.return_value = mock_resp

    res = runner.invoke(app, ["account", "overview", "--json"])
    assert res.exit_code == 0
    ov = json.loads(res.stdout)
    assert ov["account_id"] == "acc-123"
