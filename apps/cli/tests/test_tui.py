"""Async Textual tests for NEXUS TUI components, navigation, and modal dialogues."""

import pytest
from textual.widgets import DataTable, Input

from nexus_cli.registry import CommandCategory
from nexus_cli.tui.app import NexusTUIApp
from nexus_cli.tui.widgets.context import ContextPanel
from nexus_cli.tui.widgets.explorer import CommandExplorer
from nexus_cli.tui.widgets.header import StatusHeader
from nexus_cli.tui.widgets.help_modal import HelpModal
from nexus_cli.tui.widgets.palette import CommandPaletteModal
from nexus_cli.tui.widgets.sidebar import NavigationSidebar


@pytest.mark.anyio
async def test_tui_layout_and_composition():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        assert app.is_mounted
        assert app.title == "NEXUS Control Center"

        header = app.query_one(StatusHeader)
        assert header is not None

        sidebar = app.query_one(NavigationSidebar)
        assert sidebar is not None

        explorer = app.query_one(CommandExplorer)
        assert explorer is not None

        context = app.query_one(ContextPanel)
        assert context is not None


@pytest.mark.anyio
async def test_tui_command_palette_modal():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        # Trigger palette action
        app.action_palette()
        await pilot.pause()

        palette = app.screen
        assert isinstance(palette, CommandPaletteModal)

        inp = palette.query_one("#palette-search-input", Input)
        assert inp is not None

        # Dismiss palette
        palette.key_escape()
        await pilot.pause()
        assert not isinstance(app.screen, CommandPaletteModal)


@pytest.mark.anyio
async def test_tui_help_modal():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        app.action_help()
        await pilot.pause()

        help_modal = app.screen
        assert isinstance(help_modal, HelpModal)

        help_modal.key_escape()
        await pilot.pause()
        assert not isinstance(app.screen, HelpModal)


@pytest.mark.anyio
async def test_tui_explorer_filter():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        explorer = app.query_one(CommandExplorer)
        filter_inp = explorer.query_one("#command-filter-input", Input)

        # Apply filter
        filter_inp.value = "status"
        await pilot.pause()

        table = explorer.query_one("#commands-table", DataTable)
        assert table.row_count >= 1
