"""Tests for session validation, stale session auto-purge, and dynamic TUI auth toggles."""

import pytest
from unittest.mock import MagicMock, patch

from nexus_cli.config import CLIConfig, CredentialStore, load_config, save_config, validate_session
from nexus_cli.errors import AuthenticationError, NetworkError
from nexus_cli.tui.app import NexusTUIApp
from nexus_cli.tui.widgets.account_view import AccountView
from nexus_cli.tui.widgets.header import StatusHeader
from nexus_cli.tui.widgets.login_modal import LoginModal


@pytest.fixture(autouse=True)
def isolated_cli_config(tmp_path, monkeypatch):
    """Provide isolated config file and in-memory credential storage."""
    cfg_file = tmp_path / ".nexus-test-config.json"
    monkeypatch.setenv("NEXUS_CLI_CONFIG", str(cfg_file))
    monkeypatch.setenv("NEXUS_DISABLE_KEYRING", "1")
    monkeypatch.setenv("NEXUS_API_URL", "https://api.nexus.test")
    monkeypatch.setenv("NEXUS_CONTROL_PLANE_URL", "https://api.nexus.test")
    return cfg_file


def test_validate_session_purges_stale_credentials_on_401(isolated_cli_config):
    """When /api/auth/me returns 401 (e.g. account deleted from DB), credentials are automatically purged."""
    cfg = load_config()
    cfg.token = "deleted-account-token"
    cfg.refresh_token = "deleted-refresh"
    cfg.email = "deleted@nexus.local"
    save_config(cfg)

    with patch("nexus_cli.client.NexusClient.get") as mock_get:
        mock_get.side_effect = AuthenticationError("Invalid or expired token")
        res = validate_session()

    assert res is None
    cfg_after = load_config()
    assert cfg_after.token is None
    assert cfg_after.refresh_token is None
    assert cfg_after.email is None


def test_validate_session_updates_email_on_200(isolated_cli_config):
    """When /api/auth/me returns 200, session is verified and email is updated."""
    cfg = load_config()
    cfg.token = "valid-token"
    cfg.email = "old@nexus.local"
    save_config(cfg)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": 42, "email": "operator@nexus.local", "role": "admin", "is_active": True}

    with patch("nexus_cli.client.NexusClient.get", return_value=mock_resp):
        res = validate_session()

    assert res is not None
    assert res["email"] == "operator@nexus.local"
    cfg_after = load_config()
    assert cfg_after.email == "operator@nexus.local"
    assert cfg_after.token == "valid-token"


def test_validate_session_handles_offline_gracefully(isolated_cli_config):
    """When network is offline/unreachable, credentials are not wiped unless forced."""
    cfg = load_config()
    cfg.token = "valid-token"
    cfg.email = "cached@nexus.local"
    save_config(cfg)

    with patch("nexus_cli.client.NexusClient.get", side_effect=NetworkError("Connection refused")):
        res = validate_session(force=False)

    assert res is not None
    assert res.get("offline") is True

    cfg_after = load_config()
    assert cfg_after.token == "valid-token"
    assert cfg_after.email == "cached@nexus.local"


@pytest.mark.anyio
async def test_account_view_unauthenticated_state():
    """When user is unauthenticated, AccountView shows Login button and hides Logout button."""
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        account_view = app.query_one("#view-account", AccountView)
        # Force unauthenticated state
        account_view._render_account_data({
            "authenticated": False,
            "cfg": load_config(),
            "account": {},
            "data_summary": {},
            "github": {},
            "devices": [],
        })
        await pilot.pause()

        btn_login = account_view.query_one("#btn-account-login")
        btn_logout = account_view.query_one("#btn-account-logout")
        unauth_box = account_view.query_one("#unauth-account-container")
        auth_box = account_view.query_one("#auth-account-container")

        assert btn_login.display is True
        assert btn_logout.display is False
        assert unauth_box.display is True
        assert auth_box.display is False


@pytest.mark.anyio
async def test_account_view_authenticated_state():
    """When user is authenticated, AccountView hides Login button and shows Logout button."""
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        account_view = app.query_one("#view-account", AccountView)
        cfg = load_config()
        cfg.token = "dummy-token"
        cfg.email = "active@nexus.local"

        account_view._render_account_data({
            "authenticated": True,
            "cfg": cfg,
            "account": {"email": "active@nexus.local", "role": "admin", "is_active": True},
            "data_summary": {},
            "github": {},
            "devices": [],
        })
        await pilot.pause()

        btn_login = account_view.query_one("#btn-account-login")
        btn_logout = account_view.query_one("#btn-account-logout")
        unauth_box = account_view.query_one("#unauth-account-container")
        auth_box = account_view.query_one("#auth-account-container")

        assert btn_login.display is False
        assert btn_logout.display is True
        assert unauth_box.display is False
        assert auth_box.display is True


def test_login_modal_compose():
    """LoginModal composes properly with Google OAuth and token input widgets."""
    modal = LoginModal()
    assert modal._oauth_server is None
    assert not modal._stop_oauth.is_set()
