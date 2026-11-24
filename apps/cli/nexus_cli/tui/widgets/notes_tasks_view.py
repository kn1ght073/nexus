"""Knowledge & Productivity Widget for NEXUS Control Center.

Inspired by Sticky-note Kanban reference: features Tasks Kanban board (Pending, Active, Done),
Sticky Notes Wall, and Project Progress tracking.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, DataTable, Input, Label, Static

from ...client import get_client
from ...config import load_config
from .context import ContextPanel


class NotesTasksView(Static):
    """Productivity view featuring Tasks Kanban board, Notes cards, and Project metrics."""

    class ProductivityAction(Message):
        def __init__(self, action_id: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.action_id = action_id
            self.data = data or {}
            super().__init__()

    active_tab: str = "tasks"  # "tasks" | "notes" | "projects"
    _tasks_cache: List[Dict[str, Any]] = []
    _notes_cache: List[Dict[str, Any]] = []
    _projects_cache: List[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="productivity-container"):
            # Header Tab Bar
            with Horizontal(classes="view-header-bar"):
                yield Label("📋 KNOWLEDGE & PRODUCTIVITY", classes="view-title")
                with Horizontal(classes="header-actions"):
                    yield Button("📋 Tasks Kanban", id="tab-tasks", variant="primary", classes="btn-sm")
                    yield Button("📝 Notes Wall", id="tab-notes", classes="btn-sm")
                    yield Button("📁 Projects", id="tab-projects", classes="btn-sm")
                    yield Button("🔄 Refresh", id="btn-prod-refresh", classes="btn-sm")

            # Main content areas container
            with VerticalScroll(id="productivity-content-scroll"):
                # 1. Kanban Tasks Board
                with Vertical(id="section-tasks-kanban"):
                    with Horizontal(id="kanban-action-bar"):
                        yield Label("Daily Objectives & Execution Board", classes="kanban-section-title")
                        yield Button("➕ Add New Task", id="btn-add-task", variant="primary", classes="btn-sm")

                    with Horizontal(id="kanban-columns-container"):
                        # Column 1: Pending
                        with Vertical(classes="kanban-column", id="col-pending"):
                            yield Label("⏳ PENDING (To-Do)", classes="kanban-col-header")
                            yield Static("Loading tasks...", id="kanban-pending-cards", classes="kanban-cards-area")

                        # Column 2: In Progress
                        with Vertical(classes="kanban-column", id="col-in-progress"):
                            yield Label("🔄 IN PROGRESS", classes="kanban-col-header")
                            yield Static("Loading tasks...", id="kanban-active-cards", classes="kanban-cards-area")

                        # Column 3: Completed
                        with Vertical(classes="kanban-column", id="col-completed"):
                            yield Label("✅ COMPLETED", classes="kanban-col-header")
                            yield Static("Loading tasks...", id="kanban-done-cards", classes="kanban-cards-area")

                # 2. Notes Wall Section
                with Vertical(id="section-notes-wall"):
                    with Horizontal(id="notes-action-bar"):
                        yield Label("Sovereign Notes & Captured Thoughts", classes="kanban-section-title")
                        yield Input(placeholder="Search notes... (title, content)", id="notes-search-input")
                        yield Button("➕ Create Note", id="btn-add-note", variant="primary", classes="btn-sm")

                    with Vertical(id="notes-cards-container"):
                        yield Static("Loading notes wall...", id="notes-cards-static")

                # 3. Projects Section
                with Vertical(id="section-projects-list"):
                    with Horizontal(id="projects-action-bar"):
                        yield Label("Active Sovereign Projects & Milestones", classes="kanban-section-title")
                        yield Button("➕ New Project", id="btn-add-project", variant="primary", classes="btn-sm")

                    with Vertical(id="projects-table-container"):
                        table = DataTable(id="projects-table", cursor_type="row")
                        table.zebra_stripes = True
                        yield table

    def on_mount(self) -> None:
        table = self.query_one("#projects-table", DataTable)
        table.add_columns("ID", "Name", "Status", "Tasks Count", "Created At")
        self._set_tab("tasks")
        self.refresh_all_data()

    def _set_tab(self, tab: str) -> None:
        self.active_tab = tab
        try:
            self.query_one("#section-tasks-kanban", Vertical).display = (tab == "tasks")
            self.query_one("#section-notes-wall", Vertical).display = (tab == "notes")
            self.query_one("#section-projects-list", Vertical).display = (tab == "projects")

            btn_t = self.query_one("#tab-tasks", Button)
            btn_n = self.query_one("#tab-notes", Button)
            btn_p = self.query_one("#tab-projects", Button)

            btn_t.variant = "primary" if tab == "tasks" else "default"
            btn_n.variant = "primary" if tab == "notes" else "default"
            btn_p.variant = "primary" if tab == "projects" else "default"
        except Exception:
            pass

    def refresh_all_data(self) -> None:
        self.run_worker(self._fetch_all_productivity, thread=True)

    def _fetch_all_productivity(self) -> None:
        client = get_client()

        tasks = []
        try:
            r = client.get("/api/tasks", timeout=4)
            if r.status_code == 200:
                tasks = r.json()
        except Exception:
            pass

        notes = []
        try:
            r = client.get("/api/notes", timeout=4)
            if r.status_code == 200:
                notes = r.json()
        except Exception:
            pass

        projects = []
        try:
            r = client.get("/api/projects", timeout=4)
            if r.status_code == 200:
                projects = r.json()
        except Exception:
            pass

        self.app.call_from_thread(self._render_productivity, tasks, notes, projects)

    def _render_productivity(self, tasks: List[Dict[str, Any]], notes: List[Dict[str, Any]], projects: List[Dict[str, Any]]) -> None:
        if not self.is_mounted:
            return
        self._tasks_cache = tasks
        self._notes_cache = notes
        self._projects_cache = projects

        # 1. Render Kanban Columns
        pending_cards = []
        active_cards = []
        done_cards = []

        for t in tasks:
            st = t.get("status", "pending")
            tid = t.get("id")
            title = t.get("title", "Untitled Task")
            proj_id = f"#{t.get('project_id')}" if t.get("project_id") else "-"
            rev = t.get("revision", 1)

            card_str = (
                f"[bold cyan]• [{tid}][/bold cyan] [white]{title}[/white]\n"
                f"  [dim]Project: {proj_id} | Rev: {rev}[/dim]\n"
            )

            if st == "completed":
                done_cards.append(card_str)
            elif st == "in_progress":
                active_cards.append(card_str)
            else:
                pending_cards.append(card_str)

        try:
            self.query_one("#kanban-pending-cards", Static).update("\n".join(pending_cards) or "[dim]No pending tasks.[/dim]")
            self.query_one("#kanban-active-cards", Static).update("\n".join(active_cards) or "[dim]No tasks in progress.[/dim]")
            self.query_one("#kanban-done-cards", Static).update("\n".join(done_cards) or "[dim]No completed tasks.[/dim]")
        except Exception:
            pass

        # 2. Render Notes Wall (Sticky-notes styled cards)
        note_cards = []
        for n in notes:
            nid = n.get("id")
            title = n.get("title", "Untitled Note")
            content = (n.get("content") or "").replace("\n", " ")
            preview = content[:80] + ("…" if len(content) > 80 else "")
            upd = (n.get("updated_at") or "")[:19].replace("T", " ")

            card_box = (
                f"┌─ [bold cyan]📌 Note #{nid}: {title}[/bold cyan] ─────────\n"
                f"│ [white]{preview}[/white]\n"
                f"└─ [dim]Updated: {upd}[/dim]\n"
            )
            note_cards.append(card_box)

        try:
            self.query_one("#notes-cards-static", Static).update("\n".join(note_cards) or "[dim]No sovereign notes saved. Click 'Create Note' to start.[/dim]")
        except Exception:
            pass

        # 3. Render Projects Table
        try:
            table = self.query_one("#projects-table", DataTable)
            table.clear()
            for p in projects:
                pid = str(p.get("id"))
                name = p.get("name", "Project")
                status = p.get("status", "active")
                created = (p.get("created_at") or "")[:10]
                tasks_in_proj = sum(1 for t in tasks if t.get("project_id") == p.get("id"))

                table.add_row(
                    pid,
                    f"[bold cyan]{name}[/bold cyan]",
                    f"[green]{status.upper()}[/green]",
                    f"{tasks_in_proj} tasks",
                    created,
                    key=pid,
                )
            if not projects:
                table.add_row("1", "Default Sovereign Workspace", "[green]ACTIVE[/green]", f"{len(tasks)} tasks", datetime.now().strftime("%Y-%m-%d"))
        except Exception:
            pass

        # Update context panel
        try:
            ctx = self.app.query_one(ContextPanel)
            ctx.update_resource(
                title="Productivity Summary",
                subtitle="Tasks, Notes & Projects Tracking",
                properties={
                    "Total Tasks": len(tasks),
                    "Pending": len(pending_cards),
                    "In Progress": len(active_cards),
                    "Completed": len(done_cards),
                    "Notes": len(notes),
                    "Projects": len(projects),
                },
                action_label="Add Task",
                action_id="tasks.add",
                help_text="Track and advance objectives across your multi-device ecosystem.",
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "tab-tasks":
            self._set_tab("tasks")
        elif btn_id == "tab-notes":
            self._set_tab("notes")
        elif btn_id == "tab-projects":
            self._set_tab("projects")
        elif btn_id == "btn-prod-refresh":
            self.refresh_all_data()
        elif btn_id == "btn-add-task":
            self.post_message(self.ProductivityAction("add_task"))
        elif btn_id == "btn-add-note":
            self.post_message(self.ProductivityAction("add_note"))
        elif btn_id == "btn-add-project":
            self.post_message(self.ProductivityAction("add_project"))
