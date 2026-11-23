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
