"""Knowledge & Productivity Widget for NEXUS Control Center.

Features:
- Tasks Kanban board with 1-click status progression (Pending <-> In Progress <-> Completed)
- Interactive Sticky Notes Wall with 1-click Delete and Search
- Sovereign Projects Table & Deep Project Drilldown View / Modal Menu
- Add Task to Project (pre-fills/links project_id)
- Add Note to Project (pre-fills/links project_id)
- Delete Project and return to Projects List
- Project inspection with associated tasks, notes, documents/files, description, and status
- Fully working top action buttons: Add New Task, Create Note, New Project
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static

from ...client import get_client
from ...config import load_config
from ...local_store import (
    create_local_note,
    create_local_task,
    delete_local_note,
    delete_local_project,
    delete_local_task,
    list_local_notes,
    list_local_projects,
    list_local_storage_files,
    list_local_tasks,
    search_local_storage_files,
    update_local_task_status,
)
from .context import ContextPanel


class AddTaskToProjectModal(ModalScreen[Optional[Dict[str, Any]]]):
    """Modal dialog for creating and linking a task directly to a project."""

    def __init__(self, project_id: int, project_title: str) -> None:
        super().__init__()
        self.project_id = project_id
        self.project_title = project_title

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label(f"➕ ADD TASK TO PROJECT: {self.project_title} (#{self.project_id})", classes="modal-header")
            yield Static(f"[dim]Project #{self.project_id} will be linked automatically.[/dim]\n")
            yield Label("Task Title (Required):")
            yield Input(placeholder="Enter task title or objective...", id="input-modal-task-title")
            yield Label("Description (Optional):")
            yield Input(placeholder="Enter task details...", id="input-modal-task-desc")
            with Horizontal(classes="modal-footer"):
                yield Button("➕ Add Task", variant="primary", id="btn-submit-task", classes="modal-button")
                yield Button("Cancel", variant="default", id="btn-cancel-task", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-task":
            self.dismiss(None)
            return

        if event.button.id == "btn-submit-task":
            title = self.query_one("#input-modal-task-title", Input).value.strip()
            desc = self.query_one("#input-modal-task-desc", Input).value.strip()
            if not title:
                try:
                    self.notify("Task title is required", title="Validation Error", severity="error")
                except Exception:
                    pass
                return

            task_data = None
            try:
                client = get_client()
                body: Dict[str, Any] = {"title": title, "project_id": self.project_id}
                if desc:
                    body["description"] = desc
                resp = client.post("/api/tasks", json=body, timeout=4)
                if resp.status_code in (200, 201):
                    task_data = resp.json()
            except Exception:
                pass

            if not task_data:
                task_data = create_local_task(title=title, project_id=self.project_id, description=desc or None)

            self.dismiss(task_data)

    def key_escape(self) -> None:
        self.dismiss(None)


class AddNoteToProjectModal(ModalScreen[Optional[Dict[str, Any]]]):
    """Modal dialog for creating and linking a sovereign note directly to a project."""

    def __init__(self, project_id: int, project_title: str) -> None:
        super().__init__()
        self.project_id = project_id
        self.project_title = project_title

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label(f"➕ ADD NOTE TO PROJECT: {self.project_title} (#{self.project_id})", classes="modal-header")
            yield Static(f"[dim]Project #{self.project_id} will be linked automatically.[/dim]\n")
            yield Label("Note Title (Required):")
            yield Input(placeholder="Enter note title...", id="input-modal-note-title")
            yield Label("Content (Required):")
            yield Input(placeholder="Enter note body / thoughts...", id="input-modal-note-content")
            with Horizontal(classes="modal-footer"):
                yield Button("➕ Add Note", variant="primary", id="btn-submit-note", classes="modal-button")
                yield Button("Cancel", variant="default", id="btn-cancel-note", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-note":
            self.dismiss(None)
            return

        if event.button.id == "btn-submit-note":
            title = self.query_one("#input-modal-note-title", Input).value.strip()
            content = self.query_one("#input-modal-note-content", Input).value.strip()
            if not title or not content:
                try:
                    self.notify("Both note title and content are required", title="Validation Error", severity="error")
                except Exception:
                    pass
                return

            note_data = None
            try:
                client = get_client()
                body: Dict[str, Any] = {"title": title, "content": content, "project_id": self.project_id}
                resp = client.post("/api/notes", json=body, timeout=4)
                if resp.status_code in (200, 201):
                    note_data = resp.json()
            except Exception:
                pass

            if not note_data:
                note_data = create_local_note(title=title, content=content, project_id=self.project_id)

            self.dismiss(note_data)

    def key_escape(self) -> None:
        self.dismiss(None)


class ConfirmDeleteProjectModal(ModalScreen[bool]):
    """Modal confirmation dialog for destructive project removal."""

    def __init__(self, project_id: int, project_title: str) -> None:
        super().__init__()
        self.project_id = project_id
        self.project_title = project_title

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Label("🗑 DELETE SOVEREIGN PROJECT", classes="modal-header")
            yield Static(
                f"[bold red]WARNING:[/bold red] Are you sure you want to delete Project "
                f"[bold cyan]#{self.project_id}: '{self.project_title}'[/bold cyan]?\n\n"
                f"[dim]This will remove the project container permanently.[/dim]\n"
            )
            with Horizontal(classes="modal-footer"):
                yield Button("🗑 Confirm Delete", variant="error", id="btn-confirm-delete", classes="modal-button")
                yield Button("Cancel", variant="default", id="btn-cancel-delete", classes="modal-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-delete":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def key_escape(self) -> None:
        self.dismiss(False)


class ProjectDetailModal(ModalScreen[None]):
    """Full-screen modal menu for drilling down into a project, viewing and adding contents."""

    def __init__(self, project_id: int, parent_view: Optional[Any] = None) -> None:
        super().__init__()
        self.project_id = project_id
        self.parent_view = parent_view
        self._tasks: List[Dict[str, Any]] = []
        self._notes: List[Dict[str, Any]] = []
        self._project: Dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        with Vertical(classes="project-modal-box"):
            yield Label(f"📁 PROJECT #{self.project_id}", id="modal-proj-title-label", classes="modal-header")
            with Horizontal(id="modal-proj-action-bar", classes="btn-group-row"):
                yield Button("➕ Add Task to Project", id="btn-modal-add-task", variant="primary", classes="btn-sm")
                yield Button("➕ Add Note to Project", id="btn-modal-add-note", variant="primary", classes="btn-sm")
                yield Button("🗑 Delete Project", id="btn-modal-delete", variant="error", classes="btn-sm")
                yield Button("↩ Back to Projects List", id="btn-modal-back", classes="btn-sm")

            with Vertical(classes="project-summary-box"):
                yield Static("Loading project details...", id="modal-proj-meta-static")

            with Horizontal(id="modal-proj-contents-container", classes="modal-contents-row"):
                with Vertical(classes="proj-content-block"):
                    yield Label("📋 Associated Tasks", classes="kanban-col-header")
                    with VerticalScroll(id="modal-proj-tasks-scroll", classes="proj-items-scroll"):
                        yield Static("Loading tasks...", id="modal-proj-tasks-static")

                with Vertical(classes="proj-content-block"):
                    yield Label("📝 Associated Notes", classes="kanban-col-header")
                    with VerticalScroll(id="modal-proj-notes-scroll", classes="proj-items-scroll"):
                        yield Static("Loading notes...", id="modal-proj-notes-static")

                with Vertical(classes="proj-content-block"):
                    yield Label("📁 Project Documents", classes="kanban-col-header")
                    with VerticalScroll(id="modal-proj-files-scroll", classes="proj-items-scroll"):
                        yield Static("Loading documents...", id="modal-proj-files-static")

    def on_mount(self) -> None:
        self.refresh_modal_data()

    def refresh_modal_data(self) -> None:
        client = get_client()
        tasks = []
        try:
            r = client.get("/api/tasks", timeout=4)
            if r.status_code == 200:
                tasks = r.json()
        except Exception:
            pass
        if not tasks:
            tasks = list_local_tasks()

        notes = []
        try:
            r = client.get("/api/notes", timeout=4)
            if r.status_code == 200:
                notes = r.json()
        except Exception:
            pass
        if not notes:
            notes = list_local_notes()

        projects = []
        try:
            r = client.get("/api/projects", timeout=4)
            if r.status_code == 200:
                projects = r.json()
        except Exception:
            pass
        if not projects:
            projects = list_local_projects()

        self._tasks = [t for t in tasks if str(t.get("project_id")) == str(self.project_id)]
        self._notes = [n for n in notes if str(n.get("project_id")) == str(self.project_id)]
        proj = next((p for p in projects if str(p.get("id")) == str(self.project_id)), None)
        if not proj:
            proj = {"id": self.project_id, "title": f"Project #{self.project_id}", "status": "active", "description": ""}
        self._project = proj
        self._render_modal_contents()

    def _render_modal_contents(self) -> None:
        try:
            pname = self._project.get("title") or self._project.get("name", f"Project #{self.project_id}")
            status = (self._project.get("status") or "active").upper()
            desc = self._project.get("description") or "No description provided."
            created = (self._project.get("created_at") or "")[:19].replace("T", " ") or "N/A"

            lbl = self.query_one("#modal-proj-title-label", Label)
            lbl.update(f"📁 PROJECT #{self.project_id}: {pname}")

            meta = self.query_one("#modal-proj-meta-static", Static)
            meta.update(
                f"[bold]Status:[/bold] [green]{status}[/green]   "
                f"[bold]Created:[/bold] {created}   "
                f"[bold]Tasks:[/bold] {len(self._tasks)}   "
                f"[bold]Notes:[/bold] {len(self._notes)}\n"
                f"[dim]Description: {desc}[/dim]"
            )

            # Tasks
            tasks_scroll = self.query_one("#modal-proj-tasks-scroll", VerticalScroll)
            tasks_scroll.remove_children()
            if not self._tasks:
                tasks_scroll.mount(Static("[dim]No tasks associated with this project yet.[/dim]"))
            else:
                for t in self._tasks:
                    st = t.get("status", "pending")
                    st_badge = "✓" if st == "completed" else "🔄" if st == "in_progress" else "⏳"
                    tasks_scroll.mount(Static(f"[bold cyan]{st_badge} [{t.get('id')}][/bold cyan] {t.get('title')}"))

            # Notes
            notes_scroll = self.query_one("#modal-proj-notes-scroll", VerticalScroll)
            notes_scroll.remove_children()
            if not self._notes:
                notes_scroll.mount(Static("[dim]No notes associated with this project yet.[/dim]"))
            else:
                for n in self._notes:
                    preview = (n.get("content") or "").replace("\n", " ")[:80]
                    notes_scroll.mount(Static(f"📌 [bold cyan]#{n.get('id')}[/bold cyan] {n.get('title')}\n[dim]{preview}[/dim]"))

            # Files
            files_scroll = self.query_one("#modal-proj-files-scroll", VerticalScroll)
            files_scroll.remove_children()
            files = []
            try:
                files = list_local_storage_files(f"projects/{self.project_id}")
                if not files:
                    files = [f for f in list_local_storage_files("projects") if not f.get("is_dir")]
            except Exception:
                pass
            if not files:
                files_scroll.mount(Static("[dim]No files found in storage for this project.[/dim]"))
            else:
                for f in files:
                    files_scroll.mount(Static(f"📄 {f.get('name')} ({f.get('size', 0):,} B)"))
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        pname = self._project.get("title") or self._project.get("name", f"Project #{self.project_id}")

        if btn_id == "btn-modal-back":
            self.dismiss(None)
        elif btn_id == "btn-modal-add-task":
            def on_task_added(task: Optional[Dict[str, Any]]) -> None:
                if task:
                    self.refresh_modal_data()
                    if self.parent_view:
                        self.parent_view.refresh_all_data()
            self.app.push_screen(AddTaskToProjectModal(self.project_id, pname), on_task_added)
        elif btn_id == "btn-modal-add-note":
            def on_note_added(note: Optional[Dict[str, Any]]) -> None:
                if note:
                    self.refresh_modal_data()
                    if self.parent_view:
                        self.parent_view.refresh_all_data()
            self.app.push_screen(AddNoteToProjectModal(self.project_id, pname), on_note_added)
        elif btn_id == "btn-modal-delete":
            def on_delete_confirmed(confirmed: Optional[bool]) -> None:
                if confirmed:
                    try:
                        delete_local_project(self.project_id)
                    except Exception:
                        pass
                    try:
                        client = get_client()
                        client.delete(f"/api/projects/{self.project_id}", timeout=4)
                    except Exception:
                        pass
                    if self.parent_view:
                        self.parent_view.close_project()
                        self.parent_view.refresh_all_data()
                    self.dismiss(None)
            self.app.push_screen(ConfirmDeleteProjectModal(self.project_id, pname), on_delete_confirmed)

    def key_escape(self) -> None:
        self.dismiss(None)


class NotesTasksView(Static):
    """Productivity view featuring Tasks Kanban board, Notes cards, and Project metrics."""

    class ProductivityAction(Message):
        def __init__(self, action_id: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.action_id = action_id
            self.data = data or {}
            super().__init__()

    active_tab: str = "tasks"  # "tasks" | "notes" | "projects"
    selected_project_id: Optional[int] = None
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
                    # 3A. Projects Table View
                    with Vertical(id="projects-table-container"):
                        with Horizontal(id="projects-action-bar"):
                            yield Label("Active Sovereign Projects & Milestones", classes="kanban-section-title")
                            yield Button("➕ New Project", id="btn-add-project", variant="primary", classes="btn-sm")

                        table = DataTable(id="projects-table", cursor_type="row")
                        table.zebra_stripes = True
                        yield table
                        yield Static("[dim]Tip: Click or press Enter on any project to drill down into its contents and actions.[/dim]", id="projects-table-hint")

                    # 3B. Project Detail Drill-down View
                    with Vertical(id="project-detail-container"):
                        with Horizontal(id="project-detail-action-bar"):
                            yield Label("📁 PROJECT DETAIL", id="proj-detail-title-label", classes="kanban-section-title")
                            yield Button("➕ Add Task to Project", id="btn-proj-add-task", variant="primary", classes="btn-sm")
                            yield Button("➕ Add Note to Project", id="btn-proj-add-note", variant="primary", classes="btn-sm")
                            yield Button("🗑 Delete Project", id="btn-proj-delete", variant="error", classes="btn-sm")
                            yield Button("↩ Back to Projects List", id="btn-proj-back", classes="btn-sm")

                        with Vertical(id="project-detail-summary-card", classes="project-summary-box"):
                            yield Static("", id="proj-detail-meta-static")

                        with Horizontal(id="project-contents-container"):
                            # Column 1: Associated Tasks
                            with Vertical(id="proj-tasks-col", classes="proj-content-block"):
                                yield Label("📋 Associated Tasks", classes="kanban-col-header")
                                with VerticalScroll(id="proj-tasks-list", classes="proj-items-scroll"):
                                    yield Static("Loading tasks...", id="proj-tasks-placeholder")

                            # Column 2: Associated Notes
                            with Vertical(id="proj-notes-col", classes="proj-content-block"):
                                yield Label("📝 Associated Notes", classes="kanban-col-header")
                                with VerticalScroll(id="proj-notes-list", classes="proj-items-scroll"):
                                    yield Static("Loading notes...", id="proj-notes-placeholder")

                            # Column 3: Documents / Storage Files
                            with Vertical(id="proj-files-col", classes="proj-content-block"):
                                yield Label("📁 Project Documents & Files", classes="kanban-col-header")
                                with VerticalScroll(id="proj-files-list", classes="proj-items-scroll"):
                                    yield Static("Loading files...", id="proj-files-placeholder")

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

            if tab == "projects":
                self._update_project_view_visibility()
        except Exception:
            pass

    def _update_project_view_visibility(self) -> None:
        try:
            is_drilldown = self.selected_project_id is not None
            self.query_one("#projects-table-container", Vertical).display = not is_drilldown
            self.query_one("#project-detail-container", Vertical).display = is_drilldown
        except Exception:
            pass

    def open_project(self, project_id: Any) -> None:
        """Open a project drilldown view displaying all associated tasks, notes, files, and actions."""
        try:
            self.selected_project_id = int(project_id) if str(project_id).isdigit() else project_id
        except Exception:
            self.selected_project_id = project_id

        if not self._projects_cache:
            try:
                self._projects_cache = list_local_projects()
            except Exception:
                pass
        if not self._tasks_cache:
            try:
                self._tasks_cache = list_local_tasks()
            except Exception:
                pass
        if not self._notes_cache:
            try:
                self._notes_cache = list_local_notes()
            except Exception:
                pass

        self._set_tab("projects")
        self._update_project_view_visibility()
        self._render_project_drilldown()

    def close_project(self) -> None:
        """Return from project drilldown back to projects list table."""
        self.selected_project_id = None
        self._update_project_view_visibility()
        self._update_productivity_summary_context()

    def open_project_modal(self, project_id: Any) -> None:
        """Open the dedicated project detail modal screen."""
        pid = int(project_id) if str(project_id).isdigit() else 1
        self.app.push_screen(ProjectDetailModal(pid, parent_view=self))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "projects-table":
            row_key = event.row_key.value if event.row_key else None
            if not row_key and event.cursor_row is not None:
                try:
                    row_data = event.data_table.get_row_at(event.cursor_row)
                    row_key = str(row_data[0])
                except Exception:
                    pass
            if row_key:
                pid = int(row_key) if str(row_key).isdigit() else row_key
                self.open_project(pid)

    def refresh_all_data(self) -> None:
        self.run_worker(self._fetch_all_productivity, thread=True)

    def _fetch_all_productivity(self) -> None:
        client = get_client()

        tasks = []
        try:
            r = client.get("/api/tasks", timeout=2)
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
            r = client.get("/api/notes", timeout=2)
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
            r = client.get("/api/projects", timeout=2)
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
                tasks_in_proj = sum(1 for t in tasks if str(t.get("project_id")) == str(p.get("id")))

                table.add_row(
                    pid,
                    f"[bold cyan]{name}[/bold cyan]",
                    f"[green]{status.upper()}[/green]",
                    f"{tasks_in_proj} tasks",
                    created,
                    key=pid,
                )
            if not projects:
                table.add_row("1", "Default Sovereign Workspace", "[green]ACTIVE[/green]", f"{len(tasks)} tasks", datetime.now().strftime("%Y-%m-%d"), key="1")
        except Exception:
            pass

        # 4. If a project is currently open in drilldown, re-render it
        if self.selected_project_id is not None:
            self._render_project_drilldown()
        else:
            self._update_productivity_summary_context()

    def _update_productivity_summary_context(self) -> None:
        try:
            ctx = self.app.query_one(ContextPanel)
            ctx.update_resource(
                title="Productivity Summary",
                subtitle="Tasks, Notes & Projects Tracking",
                properties={
                    "Total Tasks": len(self._tasks_cache),
                    "Notes": len(self._notes_cache),
                    "Projects": len(self._projects_cache),
                    "Storage": "Sovereign Local Buffer Active",
                },
                action_label="Add Task",
                action_id="tasks.add",
                help_text="Click card action buttons directly to transition task status.",
            )
        except Exception:
            pass

    def _get_selected_project(self) -> Dict[str, Any]:
        if self.selected_project_id is not None:
            for p in self._projects_cache:
                if str(p.get("id")) == str(self.selected_project_id):
                    return p
            try:
                for p in list_local_projects():
                    if str(p.get("id")) == str(self.selected_project_id):
                        return p
            except Exception:
                pass
        return {
            "id": self.selected_project_id or 1,
            "title": f"Project #{self.selected_project_id or 1}",
            "status": "active",
            "description": "Sovereign workspace container",
            "created_at": datetime.now().isoformat(),
        }

    def _get_project_files(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        files = []
        pid = project.get("id")
        pname = (project.get("title") or project.get("name") or "").lower()
        try:
            if pid:
                files = list_local_storage_files(f"projects/{pid}")
            if not files:
                all_files = list_local_storage_files("projects")
                matched = []
                for f in all_files:
                    path_l = f.get("path", "").lower()
                    name_l = f.get("name", "").lower()
                    if pid and str(pid) in path_l:
                        matched.append(f)
                    elif pname and pname in name_l:
                        matched.append(f)
                files = matched if matched else [f for f in all_files if not f.get("is_dir")]
        except Exception:
            pass
        return files

    def _render_project_drilldown(self) -> None:
        if self.selected_project_id is None:
            return

        proj = self._get_selected_project()
        pid = proj.get("id", self.selected_project_id)
        pname = proj.get("title") or proj.get("name", f"Project #{pid}")
        status = (proj.get("status") or "active").upper()
        created = (proj.get("created_at") or "")[:19].replace("T", " ") or "N/A"
        desc = proj.get("description") or "No description provided for this project."

        # 1. Update Title Label
        try:
            lbl = self.query_one("#proj-detail-title-label", Label)
            lbl.update(f"📁 PROJECT #{pid}: {pname}")
        except Exception:
            pass

        # 2. Filter tasks and notes
        tasks_source = self._tasks_cache
        if not tasks_source:
            try:
                tasks_source = list_local_tasks()
            except Exception:
                tasks_source = []

        notes_source = self._notes_cache
        if not notes_source:
            try:
                notes_source = list_local_notes()
            except Exception:
                notes_source = []

        tasks_in_proj = [
            t for t in tasks_source
            if str(t.get("project_id")) == str(self.selected_project_id)
        ]
        notes_in_proj = [
            n for n in notes_source
            if str(n.get("project_id")) == str(self.selected_project_id)
        ]

        # 3. Documents / Files
        files_in_proj = self._get_project_files(proj)

        # 4. Summary Card
        try:
            meta_static = self.query_one("#proj-detail-meta-static", Static)
            meta_text = (
                f"[bold]Status:[/bold] [green]{status}[/green]   "
                f"[bold]Created:[/bold] {created}   "
                f"[bold]Tasks:[/bold] {len(tasks_in_proj)}   "
                f"[bold]Notes:[/bold] {len(notes_in_proj)}   "
                f"[bold]Files:[/bold] {len(files_in_proj)}\n"
                f"[dim]Description: {desc}[/dim]"
            )
            meta_static.update(meta_text)
        except Exception:
            pass

        # 5. Render Tasks Column
        try:
            tasks_box = self.query_one("#proj-tasks-list", VerticalScroll)
            tasks_box.remove_children()
            if not tasks_in_proj:
                tasks_box.mount(Static("[dim]No tasks associated with this project yet.\nClick '➕ Add Task to Project' above to add one.[/dim]"))
            else:
                for t in tasks_in_proj:
                    tid = t.get("id")
                    title = t.get("title", "Untitled Task")
                    st = t.get("status", "pending")
                    st_badge = "[green]✓ COMPLETED[/green]" if st == "completed" else "[yellow]🔄 IN PROGRESS[/yellow]" if st == "in_progress" else "[cyan]⏳ PENDING[/cyan]"
                    tasks_box.mount(Static(f"[bold cyan]• [{tid}][/bold cyan] [bold]{title}[/bold] {st_badge}"))
                    btn_row = Horizontal(classes="kanban-card-btn-row")
                    tasks_box.mount(btn_row)
                    if st == "pending":
                        btn_row.mount(Button("▶ Start", id=f"proj-task-start-{tid}", variant="primary", classes="btn-sm"))
                        btn_row.mount(Button("✓ Done", id=f"proj-task-done-{tid}", variant="success", classes="btn-sm"))
                    elif st == "in_progress":
                        btn_row.mount(Button("⏳ Pending", id=f"proj-task-pend-{tid}", classes="btn-sm"))
                        btn_row.mount(Button("✓ Done", id=f"proj-task-done-{tid}", variant="success", classes="btn-sm"))
                    else:
                        btn_row.mount(Button("↩ Reopen", id=f"proj-task-reopen-{tid}", classes="btn-sm"))
                    btn_row.mount(Button("🗑 Delete", id=f"proj-task-del-{tid}", variant="error", classes="btn-sm"))
        except Exception:
            pass

        # 6. Render Notes Column
        try:
            notes_box = self.query_one("#proj-notes-list", VerticalScroll)
            notes_box.remove_children()
            if not notes_in_proj:
                notes_box.mount(Static("[dim]No notes linked to this project yet.\nClick '➕ Add Note to Project' above to create one.[/dim]"))
            else:
                for n in notes_in_proj:
                    nid = n.get("id")
                    ntitle = n.get("title", "Untitled Note")
                    ncontent = (n.get("content") or "").replace("\n", " ")[:120]
                    notes_box.mount(Static(f"📌 [bold cyan]Note #{nid}: {ntitle}[/bold cyan]\n[dim]{ncontent}[/dim]"))
                    btn_row = Horizontal(classes="notes-card-btn-row")
                    notes_box.mount(btn_row)
                    btn_row.mount(Button(f"🗑 Delete Note #{nid}", id=f"proj-note-del-{nid}", variant="error", classes="btn-sm"))
        except Exception:
            pass

        # 7. Render Files Column
        try:
            files_box = self.query_one("#proj-files-list", VerticalScroll)
            files_box.remove_children()
            if not files_in_proj:
                files_box.mount(Static("[dim]No documents or storage files linked to this project.\nStorage directory: ~/.nexus/storage/projects[/dim]"))
            else:
                for f in files_in_proj:
                    fname = f.get("name", "file")
                    fsize = f.get("size", 0)
                    fpath = f.get("path", "-")
                    files_box.mount(Static(f"📄 [bold]{fname}[/bold] ({fsize:,} bytes)\n[dim]Path: {fpath}[/dim]"))
        except Exception:
            pass

        # 8. Update Context Panel
        try:
            ctx = self.app.query_one(ContextPanel)
            ctx.update_resource(
                title=f"Project #{pid}: {pname}",
                subtitle="Active Sovereign Project Inspection",
                properties={
                    "Status": status,
                    "Tasks Count": len(tasks_in_proj),
                    "Notes Count": len(notes_in_proj),
                    "Storage Files": len(files_in_proj),
                    "Created At": created,
                },
                action_label="Add Task",
                action_id="tasks.add",
                context_data={"project_id": pid},
                help_text="Use top actions to add tasks, notes, or delete project.",
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

    def action_add_task_to_project(self) -> None:
        """Open task creation dialog pre-filled/linked to the open project."""
        if self.selected_project_id is None:
            return
        proj = self._get_selected_project()
        pname = proj.get("title") or proj.get("name", f"Project #{self.selected_project_id}")

        def on_task_added(task: Optional[Dict[str, Any]]) -> None:
            if task:
                self._tasks_cache.append(task)
                self._render_project_drilldown()
                self.refresh_all_data()

        self.app.push_screen(AddTaskToProjectModal(self.selected_project_id, pname), on_task_added)

    def action_add_note_to_project(self) -> None:
        """Open note creation dialog pre-filled/linked to the open project."""
        if self.selected_project_id is None:
            return
        proj = self._get_selected_project()
        pname = proj.get("title") or proj.get("name", f"Project #{self.selected_project_id}")

        def on_note_added(note: Optional[Dict[str, Any]]) -> None:
            if note:
                self._notes_cache.append(note)
                self._render_project_drilldown()
                self.refresh_all_data()

        self.app.push_screen(AddNoteToProjectModal(self.selected_project_id, pname), on_note_added)

    def action_delete_current_project(self) -> None:
        """Confirm and delete the currently open project."""
        if self.selected_project_id is None:
            return
        proj = self._get_selected_project()
        pname = proj.get("title") or proj.get("name", f"Project #{self.selected_project_id}")

        def on_delete_confirmed(confirmed: Optional[bool]) -> None:
            if confirmed and self.selected_project_id is not None:
                self._delete_project(self.selected_project_id)

        self.app.push_screen(ConfirmDeleteProjectModal(self.selected_project_id, pname), on_delete_confirmed)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "tab-tasks":
            self._set_tab("tasks")
        elif btn_id == "tab-notes":
            self._set_tab("notes")
        elif btn_id == "tab-projects":
            if self.active_tab == "projects" and self.selected_project_id is not None:
                self.close_project()
            else:
                self._set_tab("projects")
        elif btn_id == "btn-prod-refresh":
            self.refresh_all_data()
        elif btn_id == "btn-add-task":
            self.post_message(self.ProductivityAction("add_task"))
        elif btn_id == "btn-add-note":
            self.post_message(self.ProductivityAction("add_note"))
        elif btn_id == "btn-add-project":
            self.post_message(self.ProductivityAction("add_project"))
        # Project Drilldown Actions
        elif btn_id == "btn-proj-add-task":
            self.action_add_task_to_project()
        elif btn_id == "btn-proj-add-note":
            self.action_add_note_to_project()
        elif btn_id == "btn-proj-delete":
            self.action_delete_current_project()
        elif btn_id == "btn-proj-back":
            self.close_project()
        # 1-click Task Status Actions (Main Kanban)
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
        # Task Status Actions (Project Drilldown)
        elif btn_id.startswith("proj-task-start-"):
            tid = int(btn_id.split("-")[-1])
            self._transition_task(tid, "in_progress")
        elif btn_id.startswith("proj-task-done-"):
            tid = int(btn_id.split("-")[-1])
            self._transition_task(tid, "completed")
        elif btn_id.startswith("proj-task-pend-"):
            tid = int(btn_id.split("-")[-1])
            self._transition_task(tid, "pending")
        elif btn_id.startswith("proj-task-reopen-"):
            tid = int(btn_id.split("-")[-1])
            self._transition_task(tid, "pending")
        elif btn_id.startswith("proj-task-del-"):
            tid = int(btn_id.split("-")[-1])
            self._delete_task(tid)
        # Note Actions (Main & Project Drilldown)
        elif btn_id.startswith("note-del-"):
            nid = int(btn_id.split("-")[-1])
            self._delete_note(nid)
        elif btn_id.startswith("proj-note-del-"):
            nid = int(btn_id.split("-")[-1])
            self._delete_note(nid)

    def key_escape(self) -> None:
        if self.selected_project_id is not None:
            self.close_project()

    def _transition_task(self, task_id: int, new_status: str) -> None:
        try:
            update_local_task_status(task_id, status=new_status)
        except Exception:
            pass
        for t in self._tasks_cache:
            if t.get("id") == task_id:
                t["status"] = new_status
        if self.selected_project_id is not None:
            self._render_project_drilldown()

        def worker():
            try:
                client = get_client()
                client.put(f"/api/tasks/{task_id}", json={"status": new_status}, timeout=4)
            except Exception:
                pass
            self.app.call_from_thread(self.refresh_all_data)

        self.run_worker(worker, thread=True)

    def _delete_task(self, task_id: int) -> None:
        try:
            delete_local_task(task_id)
        except Exception:
            pass
        self._tasks_cache = [t for t in self._tasks_cache if t.get("id") != task_id]
        if self.selected_project_id is not None:
            self._render_project_drilldown()

        def worker():
            try:
                client = get_client()
                client.delete(f"/api/tasks/{task_id}", timeout=4)
            except Exception:
                pass
            self.app.call_from_thread(self.refresh_all_data)

        self.run_worker(worker, thread=True)

    def _delete_note(self, note_id: int) -> None:
        try:
            delete_local_note(note_id)
        except Exception:
            pass
        self._notes_cache = [n for n in self._notes_cache if n.get("id") != note_id]
        if self.selected_project_id is not None:
            self._render_project_drilldown()

        def worker():
            try:
                client = get_client()
                client.delete(f"/api/notes/{note_id}", timeout=4)
            except Exception:
                pass
            self.app.call_from_thread(self.refresh_all_data)

        self.run_worker(worker, thread=True)

    def _delete_project(self, project_id: int) -> None:
        try:
            delete_local_project(project_id)
        except Exception:
            pass
        self._projects_cache = [p for p in self._projects_cache if p.get("id") != project_id]
        self.close_project()

        def worker():
            try:
                client = get_client()
                client.delete(f"/api/projects/{project_id}", timeout=4)
            except Exception:
                pass
            self.app.call_from_thread(self._after_project_deleted, project_id)

        self.run_worker(worker, thread=True)

    def _after_project_deleted(self, project_id: int) -> None:
        self.close_project()
        self.refresh_all_data()
        try:
            self.notify(f"Project #{project_id} deleted successfully.", title="PROJECT DELETED")
        except Exception:
            pass
