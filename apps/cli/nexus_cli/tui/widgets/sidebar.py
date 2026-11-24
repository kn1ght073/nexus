"""Navigation Sidebar Widget displaying hierarchical categories, views, and command counts."""

from typing import Union
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, Static, Tree

from ...registry import CommandCategory, get_registry


class NavigationSidebar(Static):
    """Sidebar providing collapsible navigation for NEXUS views and commands."""

    class ViewSelected(Message):
        """Dispatched when the user selects a cockpit view."""

        def __init__(self, view_id: str, title: str) -> None:
            self.view_id = view_id
            self.title = title
            super().__init__()

    class CategorySelected(Message):
        """Dispatched when the user selects a command category."""

        def __init__(self, category: CommandCategory) -> None:
            self.category = category
            super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="sidebar-container"):
            yield Label("NAVIGATION", id="sidebar-title")
            tree: Tree[Union[str, CommandCategory]] = Tree("NEXUS COCKPIT", id="category-tree")
            tree.root.expand()
            yield tree

    def on_mount(self) -> None:
        self.populate_categories()

    def populate_categories(self) -> None:
        tree = self.query_one("#category-tree", Tree)
        tree.clear()
        reg = get_registry()

        # Branch 1: Interactive Workspace Views
        views_node = tree.root.add("WORKSPACE VIEWS", expand=True)
        views = [
            ("view-overview", "📊 Overview Dashboard", "Overview"),
            ("view-account", "👤 Account & Identity", "Account"),
            ("view-devices", "📱 Device Management", "Devices"),
            ("view-nodes", "🖥️ Edge Nodes", "Nodes"),
            ("view-network", "🌐 Network & Relay", "Network"),
            ("view-sync", "🔄 Synchronization", "Sync"),
            ("view-files", "📁 Files & Storage", "Files"),
            ("view-notes-tasks", "📋 Notes & Tasks", "Notes & Tasks"),
            ("view-services", "⚙️ Local Services", "Services"),
            ("view-diagnostics", "🩺 Diagnostics Doctor", "Doctor"),
            ("view-activity", "🛡️ Activity & Security", "Activity"),
            ("view-settings", "🛠️ Settings & Profiles", "Settings"),
        ]
        for vid, label, title in views:
            views_node.add_leaf(label, data=f"view:{vid}:{title}")

        # Branch 2: Unified Command Explorer Categories
        commands_node = tree.root.add("COMMAND EXPLORER", expand=True)
        icons = {
            CommandCategory.OVERVIEW: "⚡",
            CommandCategory.ACCOUNT_IDENTITY: "👤",
            CommandCategory.DEVICES_NODES: "💻",
            CommandCategory.FILES_KNOWLEDGE: "📁",
            CommandCategory.PROJECTS_PRODUCTIVITY: "📋",
            CommandCategory.SYNCHRONIZATION: "🔄",
            CommandCategory.LOCAL_SERVICES: "⚙️",
            CommandCategory.SETTINGS_SETUP: "🛠️",
        }

        for cat in reg.get_categories():
            count = len(reg.list_by_category(cat))
            icon = icons.get(cat, "•")
            label = f"{icon} {cat.value} ({count})"
            commands_node.add_leaf(label, data=cat)

        tree.root.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node = event.node
        if node.data:
            if isinstance(node.data, str) and node.data.startswith("view:"):
                parts = node.data.split(":", 2)
                view_id = parts[1]
                title = parts[2] if len(parts) > 2 else view_id
                self.post_message(self.ViewSelected(view_id, title))
            elif isinstance(node.data, CommandCategory):
                self.post_message(self.CategorySelected(node.data))
