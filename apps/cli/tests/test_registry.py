"""Unit tests for Unified Command Registry."""

import pytest
from nexus_cli.registry import (
    CommandCategory,
    CommandMetadata,
    CommandResult,
    get_registry,
)


def test_registry_categories_and_count():
    reg = get_registry()
    categories = reg.get_categories()
    assert len(categories) == 8
    assert CommandCategory.OVERVIEW in categories
    assert CommandCategory.DEVICES_NODES in categories
    assert CommandCategory.ACCOUNT_IDENTITY in categories
    assert CommandCategory.SETTINGS_SETUP in categories

    commands = reg.list_all()
    assert len(commands) >= 25


def test_command_metadata_integrity():
    reg = get_registry()
    for cmd in reg.list_all():
        assert cmd.id
        assert cmd.name
        assert isinstance(cmd.category, CommandCategory)
        assert len(cmd.command_tokens) > 0
        assert cmd.summary
        assert cmd.detailed_description
        assert cmd.usage
        assert isinstance(cmd.is_destructive, bool)
        assert isinstance(cmd.requires_auth, bool)


def test_registry_search_and_filtering():
    reg = get_registry()

    # Search by token
    devices_cmds = reg.search("devices")
    assert len(devices_cmds) > 0
    assert any(c.id == "devices.list" for c in devices_cmds)

    # Search by category
    overview_cmds = reg.list_by_category(CommandCategory.OVERVIEW)
    assert any(c.id == "overview.status" for c in overview_cmds)
    assert any(c.id == "overview.doctor" for c in overview_cmds)

    # Fuzzy/partial search
    doc_cmds = reg.search("diag")
    assert any("doctor" in c.id or "diag" in c.summary.lower() for c in doc_cmds)


def test_registry_execution_version():
    reg = get_registry()
    res = reg.execute("overview.version")
    assert res.success is True
    assert "version" in res.data
    assert res.title == "NEXUS CLI Version"


def test_registry_execution_missing_handler():
    reg = get_registry()
    res = reg.execute("nonexistent.command.id")
    assert res.success is False
    assert "No execution handler" in res.error


def test_registry_new_commands_registered():
    reg = get_registry()
    pair_cmd = reg.get("nodes.pairing_code")
    assert pair_cmd is not None
    assert pair_cmd.category == CommandCategory.DEVICES_NODES

    revoke_cmd = reg.get("nodes.revoke")
    assert revoke_cmd is not None
    assert revoke_cmd.is_destructive is True

    sync_cmd = reg.get("sync.pull")
    assert sync_cmd is not None
    assert sync_cmd.category == CommandCategory.SYNCHRONIZATION


def test_registry_handlers_api_routes(monkeypatch):
    reg = get_registry()
    called_routes = []

    class MockResponse:
        def __init__(self, data, status_code=200):
            self._data = data
            self.status_code = status_code
            self.text = "ok"

        def json(self):
            return self._data

    class MockClient:
        def get(self, url, **kwargs):
            called_routes.append(("GET", url))
            return MockResponse([])

        def post(self, url, **kwargs):
            called_routes.append(("POST", url))
            return MockResponse({"code": "123456", "expires_at": "15m", "changes": {}})

        def delete(self, url, **kwargs):
            called_routes.append(("DELETE", url))
            return MockResponse({})

        def put(self, url, **kwargs):
            called_routes.append(("PUT", url))
            return MockResponse({})

    monkeypatch.setattr("nexus_cli.registry.get_client", lambda: MockClient())

    # Execute devices.list
    res = reg.execute("devices.list")
    assert res.success is True
    assert ("GET", "/api/devices") in called_routes

    # Execute nodes.pairing_code
    res = reg.execute("nodes.pairing_code")
    assert res.success is True
    assert ("POST", "/api/nodes/pair") in called_routes

    # Execute sync.pull
    res = reg.execute("sync.pull")
    assert res.success is True
    assert ("POST", "/api/sync/pull") in called_routes

    # Execute nodes.revoke
    res = reg.execute("nodes.revoke", args={"node_id": "42"})
    assert res.success is True
    assert ("DELETE", "/api/nodes/42") in called_routes
