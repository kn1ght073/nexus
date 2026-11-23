"""Navigation Sidebar Widget displaying hierarchical categories and command counts."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, Static, Tree

from ...registry import CommandCategory, get_registry


class NavigationSidebar(Static):
    """Sidebar providing collapsible category navigation for NEXUS commands."""

    class CategorySelected(Message):
        """Dispatched when the user selects a command category."""

        def __init__(self, category: CommandCategory) -> None:
            self.category = category
            super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="sidebar-container"):
            yield Label("NAVIGATION", id="sidebar-title")
            tree: Tree[CommandCategory] = Tree("NEXUS Core", id="category-tree")
            tree.root.expand()
            yield tree

    def on_mount(self) -> None:
        self.populate_categories()

    def populate_categories(self) -> None:
        tree = self.query_one("#category-tree", Tree)
        tree.clear()
        reg = get_registry()

        icons = {
            CommandCategory.OVERVIEW: "📊",
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
            tree.root.add_leaf(label, data=cat)

        tree.root.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node = event.node
        if node.data and isinstance(node.data, CommandCategory):
            self.post_message(self.CategorySelected(node.data))
