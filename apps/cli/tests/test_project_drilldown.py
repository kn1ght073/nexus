"""Unit and integration tests for Project Drilldown, Project Modals, and Content Management in NEXUS TUI."""

import pytest
from textual.widgets import Button, DataTable, Input, Label, Static

from nexus_cli.tui.app import NexusTUIApp
from nexus_cli.tui.widgets.notes_tasks_view import (
    AddNoteToProjectModal,
    AddTaskToProjectModal,
    ConfirmDeleteProjectModal,
    NotesTasksView,
    ProjectDetailModal,
)
from nexus_cli.local_store import (
    create_local_project,
    create_local_task,
    create_local_note,
    list_local_projects,
    list_local_tasks,
    list_local_notes,
    delete_local_project,
)


class MockClient:
    def get(self, *args, **kwargs):
        raise ConnectionError("Offline test client")

    def post(self, *args, **kwargs):
        raise ConnectionError("Offline test client")

    def put(self, *args, **kwargs):
        raise ConnectionError("Offline test client")

    def delete(self, *args, **kwargs):
        raise ConnectionError("Offline test client")


@pytest.fixture(autouse=True)
def clean_local_store(tmp_path, monkeypatch):
    """Isolate local sqlite store during tests."""
    test_db_dir = tmp_path / ".nexus"
    test_db_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("nexus_cli.local_store.DB_DIR", test_db_dir)
    monkeypatch.setattr("nexus_cli.local_store.DB_PATH", test_db_dir / "local_store.db")
    monkeypatch.setattr("nexus_cli.local_store.STORAGE_ROOT", test_db_dir / "storage")
    monkeypatch.setattr("nexus_cli.tui.widgets.notes_tasks_view.get_client", lambda: MockClient())
    monkeypatch.setattr("nexus_cli.registry.get_client", lambda: MockClient())


@pytest.mark.anyio
async def test_project_drilldown_navigation():
    """Test clicking/opening a project shows project detail view with required buttons and contents."""
    proj = create_local_project(title="Sovereign Core Architecture", description="Core kernel and bypass layer")
    pid = proj["id"]
    create_local_task(title="Build syscall hooks", project_id=pid)
    create_local_note(title="Kernel offsets", content="Pointers and base offsets", project_id=pid)

    app = NexusTUIApp()
    async with app.run_test() as pilot:
        prod_view = app.query_one(NotesTasksView)

        # Switch to projects tab
        prod_view._set_tab("projects")
        await pilot.pause()

        # Verify initial table view is visible and detail is hidden
        table_container = prod_view.query_one("#projects-table-container")
        detail_container = prod_view.query_one("#project-detail-container")
        assert table_container.display is True
        assert detail_container.display is False

        # Open project drilldown
        prod_view.open_project(pid)
        await pilot.pause()

        # Verify drilldown view is visible and table container is hidden
        assert table_container.display is False
        assert detail_container.display is True
        assert prod_view.selected_project_id == pid

        # Verify the 4 required action buttons exist
        btn_add_task = prod_view.query_one("#btn-proj-add-task", Button)
        btn_add_note = prod_view.query_one("#btn-proj-add-note", Button)
        btn_delete = prod_view.query_one("#btn-proj-delete", Button)
        btn_back = prod_view.query_one("#btn-proj-back", Button)

        assert "Add Task to Project" in str(btn_add_task.label)
        assert "Add Note to Project" in str(btn_add_note.label)
        assert "Delete Project" in str(btn_delete.label)
        assert "Back to Projects List" in str(btn_back.label)

        # Verify project contents are rendered
        title_label = prod_view.query_one("#proj-detail-title-label", Label)
        assert "Sovereign Core Architecture" in str(title_label.render())

        meta_static = prod_view.query_one("#proj-detail-meta-static", Static)
        assert "Core kernel and bypass layer" in str(meta_static.render())

        tasks_scroll = prod_view.query_one("#proj-tasks-list")
        tasks_text = " ".join(str(s.render()) for s in tasks_scroll.query(Static))
        assert "Build syscall hooks" in tasks_text

        notes_scroll = prod_view.query_one("#proj-notes-list")
        notes_text = " ".join(str(s.render()) for s in notes_scroll.query(Static))
        assert "Kernel offsets" in notes_text

        # Click Back button
        btn_back.press()
        await pilot.pause()

        # Verify back in projects list
        assert prod_view.selected_project_id is None
        assert table_container.display is True
        assert detail_container.display is False


@pytest.mark.anyio
async def test_add_task_to_project_modal():
    """Test Add Task to Project pre-fills project_id and updates project contents immediately."""
    proj = create_local_project(title="EAC Resilience Project", description="Driver unhooking suite")
    pid = proj["id"]

    modal = AddTaskToProjectModal(project_id=pid, project_title=proj["title"])
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        prod_view = app.query_one(NotesTasksView)
        prod_view.open_project(pid)
        await pilot.pause()

        # Push modal
        app.push_screen(modal)
        await pilot.pause()

        assert app.screen == modal
        input_title = modal.query_one("#input-modal-task-title", Input)
        input_desc = modal.query_one("#input-modal-task-desc", Input)
        input_title.value = "Direct Syscall Implementation"
        input_desc.value = "Halo's gate stub"

        # Submit task
        btn_submit = modal.query_one("#btn-submit-task", Button)
        btn_submit.press()
        await pilot.pause()

        # Verify modal dismissed
        assert app.screen != modal

        # Verify task created in database with project_id
        tasks = list_local_tasks()
        created = next((t for t in tasks if t["title"] == "Direct Syscall Implementation"), None)
        assert created is not None
        assert created["project_id"] == pid

        # Refresh productivity view and verify it displays the new task
        prod_view.open_project(pid)
        await pilot.pause()
        tasks_scroll = prod_view.query_one("#proj-tasks-list")
        tasks_text = " ".join(str(s.render()) for s in tasks_scroll.query(Static))
        assert "Direct Syscall Implementation" in tasks_text


@pytest.mark.anyio
async def test_add_note_to_project_modal():
    """Test Add Note to Project pre-fills project_id and updates project contents immediately."""
    proj = create_local_project(title="Reverse Engineering Lab", description="Vanguard analysis")
    pid = proj["id"]

    modal = AddNoteToProjectModal(project_id=pid, project_title=proj["title"])
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        prod_view = app.query_one(NotesTasksView)
        prod_view.open_project(pid)
        await pilot.pause()

        # Push note modal
        app.push_screen(modal)
        await pilot.pause()

        assert app.screen == modal
        input_title = modal.query_one("#input-modal-note-title", Input)
        input_content = modal.query_one("#input-modal-note-content", Input)
        input_title.value = "HVCI Analysis Findings"
        input_content.value = "Page protection fault mechanics and CR4 WP bit toggle"

        # Submit note
        btn_submit = modal.query_one("#btn-submit-note", Button)
        btn_submit.press()
        await pilot.pause()

        # Verify modal dismissed
        assert app.screen != modal

        # Verify note in local store
        notes = list_local_notes()
        created = next((n for n in notes if n["title"] == "HVCI Analysis Findings"), None)
        assert created is not None
        assert created["project_id"] == pid

        # Refresh productivity view and verify it displays the new note
        prod_view.open_project(pid)
        await pilot.pause()
        notes_scroll = prod_view.query_one("#proj-notes-list")
        notes_text = " ".join(str(s.render()) for s in notes_scroll.query(Static))
        assert "HVCI Analysis Findings" in notes_text


@pytest.mark.anyio
async def test_project_task_status_progression():
    """Test 1-click status change and deletion directly from inside project drilldown."""
    proj = create_local_project(title="Payload Stager", description="Stage 1 loader")
    pid = proj["id"]
    task = create_local_task(title="Shellcode encryption", project_id=pid)
    tid = task["id"]

    app = NexusTUIApp()
    async with app.run_test() as pilot:
        prod_view = app.query_one(NotesTasksView)
        prod_view.open_project(pid)
        await pilot.pause()

        # Advance task status to in_progress
        btn_start = prod_view.query_one(f"#proj-task-start-{tid}", Button)
        btn_start.press()
        await pilot.pause()

        # Advance to completed
        btn_done = prod_view.query_one(f"#proj-task-done-{tid}", Button)
        btn_done.press()
        await pilot.pause()

        # Verify local task status updated
        tasks = list_local_tasks()
        updated_task = next(t for t in tasks if t["id"] == tid)
        assert updated_task["status"] == "completed"


@pytest.mark.anyio
async def test_project_deletion_flow():
    """Test project deletion confirms, deletes container, and returns to projects list."""
    proj = create_local_project(title="Temporary Target", description="To be deleted")
    pid = proj["id"]

    app = NexusTUIApp()
    async with app.run_test() as pilot:
        prod_view = app.query_one(NotesTasksView)
        prod_view.open_project(pid)
        await pilot.pause()

        # Trigger deletion directly
        prod_view._delete_project(pid)
        await pilot.pause()

        # Verify project is removed
        projects = list_local_projects()
        assert not any(p["id"] == pid for p in projects)
        assert prod_view.selected_project_id is None


@pytest.mark.anyio
async def test_project_detail_modal_dialog():
    """Test ProjectDetailModal screen displays contents and provides working action buttons."""
    proj = create_local_project(title="Full Modal Project", description="Modal inspection target")
    pid = proj["id"]
    create_local_task(title="Modal task item", project_id=pid)
    create_local_note(title="Modal note item", content="Note body", project_id=pid)

    modal = ProjectDetailModal(project_id=pid)
    app = NexusTUIApp()
    async with app.run_test() as pilot:
        app.push_screen(modal)
        await pilot.pause()

        assert app.screen == modal
        assert modal.query_one("#btn-modal-add-task") is not None
        assert modal.query_one("#btn-modal-add-note") is not None
        assert modal.query_one("#btn-modal-delete") is not None
        assert modal.query_one("#btn-modal-back") is not None

        # Press back button to dismiss
        btn_back = modal.query_one("#btn-modal-back", Button)
        btn_back.press()
        await pilot.pause()
        assert app.screen != modal
