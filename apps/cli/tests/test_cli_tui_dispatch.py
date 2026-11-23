"""Unit tests for CLI vs TUI entry point routing."""

from unittest.mock import MagicMock, patch
import pytest
from typer.testing import CliRunner

from nexus_cli.cli import app
from nexus_cli import __version__

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_cli(tmp_path, monkeypatch):
    cfg_file = tmp_path / "dispatch_test_config.json"
    monkeypatch.setenv("NEXUS_CLI_CONFIG", str(cfg_file))
    monkeypatch.setenv("NEXUS_DISABLE_KEYRING", "1")


def test_cli_help_in_non_interactive():
    # In non-interactive mode (CliRunner default), no-arg invocation prints help
    res = runner.invoke(app, [])
    assert res.exit_code == 0
    assert "NEXUS CLI" in res.stdout
    assert "auth" in res.stdout
    assert "devices" in res.stdout


def test_cli_explicit_no_ui_flag():
    res = runner.invoke(app, ["--no-ui"])
    assert res.exit_code == 0
    assert "NEXUS CLI" in res.stdout


@patch("nexus_cli.cli.is_interactive_terminal", return_value=True)
@patch("nexus_cli.tui.app.NexusTUIApp.run")
def test_cli_interactive_launches_tui(mock_tui_run, mock_is_interactive):
    res = runner.invoke(app, [])
    assert res.exit_code == 0
    assert mock_tui_run.called


@patch("nexus_cli.tui.app.NexusTUIApp.run")
def test_cli_ui_subcommand_launches_tui(mock_tui_run):
    res = runner.invoke(app, ["ui"])
    assert res.exit_code == 0
    assert mock_tui_run.called
