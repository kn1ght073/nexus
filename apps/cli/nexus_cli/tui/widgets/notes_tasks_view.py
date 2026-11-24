"""Knowledge & Productivity Widget for NEXUS Control Center.

Features:
- Tasks Kanban board with 1-click status progression (Pending <-> In Progress <-> Completed)
- Interactive Sticky Notes Wall with 1-click Delete and Search
- Sovereign Projects Table
- Fully working top action buttons: Add New Task, Create Note, New Project
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, DataTable, Input, Label, Static

from ...client import get_client
from ...config import load_config
from ...local_store import (
    delete_local_note,
    delete_local_project,
    delete_local_task,
    list_local_notes,
    list_local_projects,
    list_local_tasks,
    update_local_task_status,
)
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
                        yield Label("Daily Objectives & Execution Board — Click [Advance] or [Complete] to change status", classes="kanban-section-title")
                        yield Button("➕ Add New Task", id="btn-add-task", variant="primary", classes="btn-sm")

                    with Horizontal(id="kanban-columns-container"):
                        # Column 1: Pending
                        with Vertical(classes="kanban-column", id="col-pending"):
                            yield Label("⏳ PENDING (To-Do)", classes="kanban-col-header")
                            with VerticalScroll(id="kanban-pending-cards", classes="kanban-cards-area"):
                                yield Static("Loading tasks...", id="pending-placeholder")

                        # Column 2: In Progress
                        with Vertical(classes="kanban-column", id="col-in-progress"):
                            yield Label("🔄 IN PROGRESS", classes="kanban-col-header")
                            with VerticalScroll(id="kanban-active-cards", classes="kanban-cards-area"):
                                yield Static("Loading tasks...", id="active-placeholder")

                        # Column 3: Completed
                        with Vertical(classes="kanban-column", id="col-completed"):
                            yield Label("✅ COMPLETED", classes="kanban-col-header")
                            with VerticalScroll(id="kanban-done-cards", classes="kanban-cards-area"):
                                yield Static("Loading tasks...", id="done-placeholder")

                # 2. Notes Wall Section
                with Vertical(id="section-notes-wall"):
                    with Horizontal(id="notes-action-bar"):
                        yield Label("Sovereign Notes & Captured Thoughts", classes="kanban-section-title")
                        yield Input(placeholder="Search notes... (title, content)", id="notes-search-input")
                        yield Button("➕ Create Note", id="btn-add-note", variant="primary", classes="btn-sm")

                    with VerticalScroll(id="notes-cards-container"):
                        yield Static("Loading notes wall...", id="notes-cards-static")
                        with Vertical(id="notes-dynamic-cards"):
                            pass

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
        if not tasks:
            try:
                tasks = list_local_tasks()
            except Exception:
                pass

        notes = []
        try:
            r = client.get("/api/notes", timeout=4)
            if r.status_code == 200:
                notes = r.json()
        except Exception:
            pass
        if not notes:
            try:
                notes = list_local_notes()
            except Exception:
                pass

        projects = []
        try:
            r = client.get("/api/projects", timeout=4)
            if r.status_code == 200:
                projects = r.json()
        except Exception:
            pass
        if not projects:
            try:
                projects = list_local_projects()
            except Exception:
                pass

        self.app.call_from_thread(self._render_productivity, tasks, notes, projects)

    def _render_productivity(self, tasks: List[Dict[str, Any]], notes: List[Dict[str, Any]], projects: List[Dict[str, Any]]) -> None:
        if not self.is_mounted:
            return
        self._tasks_cache = tasks
        self._notes_cache = notes
        self._projects_cache = projects

        # 1. Render Interactive Kanban Columns
        self._render_kanban_columns(tasks)

        # 2. Render Interactive Notes Wall
        filter_q = ""
        try:
            filter_q = self.query_one("#notes-search-input", Input).value
        except Exception:
            pass
        self._render_notes_wall(filter_q)

        # 3. Render Projects Table
        try:
            table = self.query_one("#projects-table", DataTable)
            table.clear()
            for p in projects:
                pid = str(p.get("id"))
                name = p.get("title") or p.get("name", "Project")
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
                    "Notes": len(notes),
                    "Projects": len(projects),
                    "Storage": "Sovereign Local Buffer Active",
                },
                action_label="Add Task",
                action_id="tasks.add",
                help_text="Click card action buttons directly to transition task status.",
            )
        except Exception:
            pass

    def _render_kanban_columns(self, tasks: List[Dict[str, Any]]) -> None:
        try:
            pending_box = self.query_one("#kanban-pending-cards", VerticalScroll)
            active_box = self.query_one("#kanban-active-cards", VerticalScroll)
            done_box = self.query_one("#kanban-done-cards", VerticalScroll)

            pending_box.remove_children()
            active_box.remove_children()
            done_box.remove_children()

            pending_items = [t for t in tasks if (t.get("status") or "pending") not in ("in_progress", "completed")]
            active_items = [t for t in tasks if t.get("status") == "in_progress"]
            done_items = [t for t in tasks if t.get("status") == "completed"]

            if not pending_items:
                pending_box.mount(Static("[dim]No pending tasks.[/dim]"))
            else:
                for t in pending_items:
                    tid = t.get("id")
                    title = t.get("title", "Untitled Task")
                    proj = f"#{t.get('project_id')}" if t.get("project_id") else "-"
                    pending_box.mount(Static(f"[bold cyan]• [{tid}][/bold cyan] [bold]{title}[/bold]\n[dim]Project: {proj}[/dim]"))
                    btn_row = Horizontal(classes="kanban-card-btn-row")
                    pending_box.mount(btn_row)
                    btn_row.mount(Button("▶ Start", id=f"task-act-start-{tid}", variant="primary", classes="btn-sm"))
                    btn_row.mount(Button("✓ Done", id=f"task-act-done-{tid}", variant="success", classes="btn-sm"))

            if not active_items:
                active_box.mount(Static("[dim]No tasks in progress.[/dim]"))
            else:
                for t in active_items:
                    tid = t.get("id")
                    title = t.get("title", "Untitled Task")
                    proj = f"#{t.get('project_id')}" if t.get("project_id") else "-"
                    active_box.mount(Static(f"[bold cyan]• [{tid}][/bold cyan] [bold]{title}[/bold]\n[dim]Project: {proj}[/dim]"))
                    btn_row = Horizontal(classes="kanban-card-btn-row")
                    active_box.mount(btn_row)
                    btn_row.mount(Button("⏳ Pending", id=f"task-act-pend-{tid}", classes="btn-sm"))
                    btn_row.mount(Button("✓ Complete", id=f"task-act-done-{tid}", variant="success", classes="btn-sm"))

            if not done_items:
                done_box.mount(Static("[dim]No completed tasks.[/dim]"))
            else:
                for t in done_items:
                    tid = t.get("id")
                    title = t.get("title", "Untitled Task")
                    proj = f"#{t.get('project_id')}" if t.get("project_id") else "-"
                    done_box.mount(Static(f"[strike][dim]• [{tid}] {title}[/dim][/strike]\n[dim]Project: {proj}[/dim]"))
                    btn_row = Horizontal(classes="kanban-card-btn-row")
                    done_box.mount(btn_row)
                    btn_row.mount(Button("↩ Reopen", id=f"task-act-reopen-{tid}", classes="btn-sm"))
                    btn_row.mount(Button("🗑 Delete", id=f"task-act-del-{tid}", variant="error", classes="btn-sm"))
        except Exception:
            pass

    def _render_notes_wall(self, filter_q: str = "") -> None:
        q = filter_q.strip().lower()
        try:
            static_label = self.query_one("#notes-cards-static", Static)
            dynamic_box = self.query_one("#notes-dynamic-cards", Vertical)
            dynamic_box.remove_children()

            matching = []
            note_cards_text = []
            for n in self._notes_cache:
                title = n.get("title", "Untitled Note")
                content = n.get("content", "")
                if q and (q not in title.lower() and q not in content.lower()):
                    continue
                matching.append(n)
                preview = (content or "").replace("\n", " ")[:120]
                note_cards_text.append(f"📌 Note #{n.get('id')}: {title}\n{preview}")

            combined_text = "\n\n".join(note_cards_text)
            if not matching:
                empty_msg = f"No notes matching '{filter_q}'." if q else "No sovereign notes saved. Click 'Create Note' to start."
                static_label.update(empty_msg)
                return

            static_label.update(combined_text)

            for n in matching:
                nid = n.get("id")
                btn_row = Horizontal(classes="notes-card-btn-row")
                dynamic_box.mount(btn_row)
                btn_row.mount(Button(f"🗑 Delete Note #{nid}", id=f"note-del-{nid}", variant="error", classes="btn-sm"))
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "notes-search-input":
            self._render_notes_wall(filter_q=event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "notes-search-input":
            self._render_notes_wall(filter_q=event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
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
        # 1-click Task Status Actions
        elif btn_id.startswith("task-act-start-"):
            tid = int(btn_id.split("-")[-1])
            self._transition_task(tid, "in_progress")
        elif btn_id.startswith("task-act-done-"):
            tid = int(btn_id.split("-")[-1])
            self._transition_task(tid, "completed")
        elif btn_id.startswith("task-act-pend-"):
            tid = int(btn_id.split("-")[-1])
            self._transition_task(tid, "pending")
        elif btn_id.startswith("task-act-reopen-"):
            tid = int(btn_id.split("-")[-1])
            self._transition_task(tid, "pending")
        elif btn_id.startswith("task-act-del-"):
            tid = int(btn_id.split("-")[-1])
            self._delete_task(tid)
        # Note Actions
        elif btn_id.startswith("note-del-"):
            nid = int(btn_id.split("-")[-1])
            self._delete_note(nid)

    def _transition_task(self, task_id: int, new_status: str) -> None:
        def worker():
            try:
                client = get_client()
                client.put(f"/api/tasks/{task_id}", json={"status": new_status}, timeout=4)
            except Exception:
                pass
            try:
                update_local_task_status(task_id, status=new_status)
            except Exception:
                pass
            self.app.call_from_thread(self.refresh_all_data)

        self.run_worker(worker, thread=True)

    def _delete_task(self, task_id: int) -> None:
        def worker():
            try:
                client = get_client()
                client.delete(f"/api/tasks/{task_id}", timeout=4)
            except Exception:
                pass
            try:
                delete_local_task(task_id)
            except Exception:
                pass
            self.app.call_from_thread(self.refresh_all_data)

        self.run_worker(worker, thread=True)

    def _delete_note(self, note_id: int) -> None:
        def worker():
            try:
                client = get_client()
                client.delete(f"/api/notes/{note_id}", timeout=4)
            except Exception:
                pass
            try:
                delete_local_note(note_id)
            except Exception:
                pass
            self.app.call_from_thread(self.refresh_all_data)

        self.run_worker(worker, thread=True)
