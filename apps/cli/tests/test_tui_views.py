"""Comprehensive automated test suite for NEXUS Modernized TUI Views & Cockpit Dashboard."""

import pytest
from textual import events
from textual.geometry import Size
from textual.widgets import ContentSwitcher, DataTable, Input, Label, Static, Switch

from nexus_cli.config import load_config, mask_email_address, save_config
from nexus_cli.tui.app import NexusTUIApp
from nexus_cli.tui.widgets.account_view import AccountView
from nexus_cli.tui.widgets.activity_view import ActivityView
from nexus_cli.tui.widgets.context import ContextPanel
from nexus_cli.tui.widgets.devices_view import DevicesView
from nexus_cli.tui.widgets.diagnostics_view import DiagnosticsView
from nexus_cli.tui.widgets.files_view import FilesView
from nexus_cli.tui.widgets.header import StatusHeader
from nexus_cli.tui.widgets.network_view import NetworkView
from nexus_cli.tui.widgets.nodes_view import NodesView
from nexus_cli.tui.widgets.notes_tasks_view import NotesTasksView
from nexus_cli.tui.widgets.overview import OverviewDashboard
from nexus_cli.tui.widgets.services_view import ServicesView
from nexus_cli.tui.widgets.settings_view import SettingsView
from nexus_cli.tui.widgets.sidebar import NavigationSidebar
from nexus_cli.tui.widgets.sync_view import SyncView


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    cfg_file = tmp_path / "tui_views_test_config.json"
    monkeypatch.setenv("NEXUS_CLI_CONFIG", str(cfg_file))
    monkeypatch.setenv("NEXUS_DISABLE_KEYRING", "1")
    monkeypatch.delenv("NEXUS_TOKEN", raising=False)
    monkeypatch.delenv("NEXUS_API_URL", raising=False)


@pytest.mark.anyio
async def test_all_views_mounted_and_accessible():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        assert app.is_mounted

        # Verify all views are instantiated in ContentSwitcher
        switcher = app.query_one("#main-content-switcher", ContentSwitcher)
        assert switcher is not None
        assert switcher.current == "view-overview"

        assert app.query_one(OverviewDashboard) is not None
        assert app.query_one(AccountView) is not None
        assert app.query_one(DevicesView) is not None
        assert app.query_one(NodesView) is not None
        assert app.query_one(NetworkView) is not None
        assert app.query_one(SyncView) is not None
        assert app.query_one(FilesView) is not None
        assert app.query_one(NotesTasksView) is not None
        assert app.query_one(ServicesView) is not None
        assert app.query_one(DiagnosticsView) is not None
        assert app.query_one(ActivityView) is not None
        assert app.query_one(SettingsView) is not None


@pytest.mark.anyio
async def test_view_switching_navigation():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        switcher = app.query_one("#main-content-switcher", ContentSwitcher)

        # Switch to Devices View
        app.switch_to_view("view-devices")
        await pilot.pause()
        assert switcher.current == "view-devices"

        # Switch to Nodes View
        app.switch_to_view("view-nodes")
        await pilot.pause()
        assert switcher.current == "view-nodes"

        # Switch to Files View
        app.switch_to_view("view-files")
        await pilot.pause()
        assert switcher.current == "view-files"

        # Switch to Settings View
        app.switch_to_view("view-settings")
        await pilot.pause()
        assert switcher.current == "view-settings"

        # Switch back to Overview
        app.switch_to_view("view-overview")
        await pilot.pause()
        assert switcher.current == "view-overview"


@pytest.mark.anyio
async def test_overview_dashboard_structure():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        overview = app.query_one(OverviewDashboard)
        assert overview is not None

        # Check section cards
        assert overview.query_one("#card-account") is not None
        assert overview.query_one("#card-node") is not None
        assert overview.query_one("#card-devices") is not None
        assert overview.query_one("#card-sync") is not None
        assert overview.query_one("#card-system-health") is not None
        assert overview.query_one("#card-recent-activity") is not None

        # Check activity table
        act_table = overview.query_one("#overview-activity-table", DataTable)
        assert act_table is not None


@pytest.mark.anyio
async def test_overview_quick_action_switch():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        overview = app.query_one(OverviewDashboard)
        switcher = app.query_one("#main-content-switcher", ContentSwitcher)

        # Click device fleet quick action
        btn_devs = overview.query_one("#act-devices")
        btn_devs.press()
        await pilot.pause()
        assert switcher.current == "view-devices"


@pytest.mark.anyio
async def test_account_view_privacy_mask():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        account_view = app.query_one(AccountView)
        sw = account_view.query_one("#switch-mask-email", Switch)

        # Toggle mask email switch
        sw.post_message(Switch.Changed(sw, True))
        await pilot.pause()

        cfg = load_config()
        assert cfg.mask_email is True

        # Test helper function
        masked = mask_email_address("operator.nexus@example.com")
        assert masked == "o***s@example.com"


@pytest.mark.anyio
async def test_devices_view_filter_and_table():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        dev_view = app.query_one(DevicesView)
        inp = dev_view.query_one("#device-filter-input", Input)
        inp.value = "macbook"
        await pilot.pause()

        table = dev_view.query_one("#devices-table", DataTable)
        assert table is not None


@pytest.mark.anyio
async def test_nodes_view_structure():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        nodes_view = app.query_one(NodesView)
        assert nodes_view.query_one("#nodes-table", DataTable) is not None
        assert nodes_view.query_one("#btn-node-claim") is not None
        assert nodes_view.query_one("#btn-node-pair-code") is not None


@pytest.mark.anyio
async def test_network_view_topology_rendering():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        net_view = app.query_one(NetworkView)
        diag = net_view.query_one("#net-topology-diagram", Static)
        assert diag is not None

        links_table = net_view.query_one("#relay-links-table", DataTable)
        assert links_table is not None


@pytest.mark.anyio
async def test_sync_view_structure():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        sync_view = app.query_one(SyncView)
        assert sync_view.query_one("#btn-sync-pull") is not None
        assert sync_view.query_one("#sync-devices-table", DataTable) is not None
        assert sync_view.query_one("#sync-conflicts-static", Static) is not None


@pytest.mark.anyio
async def test_files_view_breadcrumbs_and_preview():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        files_view = app.query_one(FilesView)
        bc = files_view.query_one("#files-breadcrumb-path", Label)
        assert "storage roots" in str(bc.render())

        preview = files_view.query_one("#files-preview-static", Static)
        assert preview is not None

        table = files_view.query_one("#files-table", DataTable)
        assert table is not None


@pytest.mark.anyio
async def test_notes_tasks_kanban_tabs():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        prod_view = app.query_one(NotesTasksView)

        # Check initial Kanban columns
        assert prod_view.query_one("#col-pending") is not None
        assert prod_view.query_one("#col-in-progress") is not None
        assert prod_view.query_one("#col-completed") is not None

        # Switch to Notes Wall tab
        btn_notes = prod_view.query_one("#tab-notes")
        btn_notes.press()
        await pilot.pause()
        assert prod_view.active_tab == "notes"

        # Switch to Projects tab
        btn_proj = prod_view.query_one("#tab-projects")
        btn_proj.press()
        await pilot.pause()
        assert prod_view.active_tab == "projects"


@pytest.mark.anyio
async def test_services_view_cards():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        svc_view = app.query_one(ServicesView)
        assert svc_view.query_one("#svc-card-llm") is not None
        assert svc_view.query_one("#svc-card-stt") is not None
        assert svc_view.query_one("#svc-card-daemon") is not None
        assert svc_view.query_one("#svc-card-bootstrap") is not None


@pytest.mark.anyio
async def test_diagnostics_view_probes():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        diag_view = app.query_one(DiagnosticsView)
        table = diag_view.query_one("#diagnostics-table", DataTable)
        assert table is not None
        assert diag_view.query_one("#btn-diag-run") is not None
        assert diag_view.query_one("#btn-diag-export") is not None


@pytest.mark.anyio
async def test_activity_view_timeline():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        act_view = app.query_one(ActivityView)
        table = act_view.query_one("#activity-table", DataTable)
        assert table is not None
        assert act_view.query_one("#activity-filter-input", Input) is not None


@pytest.mark.anyio
async def test_settings_view_theme_toggle():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        settings_view = app.query_one(SettingsView)

        # Click Synthwave Theme
        btn_synth = settings_view.query_one("#theme-synthwave")
        btn_synth.press()
        await pilot.pause()

        cfg = load_config()
        assert cfg.theme == "synthwave"


@pytest.mark.anyio
async def test_responsive_layout_resizing():
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        ctx = app.query_one("#ctx-panel", ContextPanel)
        sidebar = app.query_one("#nav-sidebar", NavigationSidebar)

        # Narrow terminal: < 115 width collapses context panel
        app.on_resize(events.Resize(Size(100, 30), Size(100, 30)))
        await pilot.pause()
        assert ctx.display is False
        assert sidebar.display is True

        # Very narrow terminal: < 75 width collapses sidebar too
        app.on_resize(events.Resize(Size(70, 30), Size(70, 30)))
        await pilot.pause()
        assert ctx.display is False
        assert sidebar.display is False

        # Wide terminal: >= 115 restores both
        app.on_resize(events.Resize(Size(140, 30), Size(140, 30)))
        await pilot.pause()
        assert ctx.display is True
        assert sidebar.display is True
