import requests
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Input, DataTable, Button, Label
from textual.screen import ModalScreen
from config import load_config
import os

config = load_config()

def get_headers():
    return {"Authorization": "Bearer mock-token-123"}

ASCII_BANNER = """
[bold cyan]
███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
[/bold cyan]
"""

class NexusHeader(Static):
    def render(self) -> str:
        return ASCII_BANNER

class AddProjectScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("[bold cyan]Add New Project[/bold cyan]", id="modal-title")
            yield Input(placeholder="Project Title", id="project-title")
            yield Input(placeholder="Description (optional)", id="project-desc")
            with Horizontal(id="modal-buttons"):
                yield Button("Create", variant="success", id="submit")
                yield Button("Cancel", variant="error", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "submit":
            title = self.query_one("#project-title", Input).value
            desc = self.query_one("#project-desc", Input).value
            if title:
                self.dismiss({"title": title, "description": desc})

class AddTaskScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("[bold cyan]Add New Task[/bold cyan]", id="modal-title")
            yield Input(placeholder="Task Title", id="task-title")
            yield Input(placeholder="Project ID (number)", id="project-id")
            with Horizontal(id="modal-buttons"):
                yield Button("Create", variant="success", id="submit")
                yield Button("Cancel", variant="error", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "submit":
            title = self.query_one("#task-title", Input).value
            pid = self.query_one("#project-id", Input).value
            if title and pid.isdigit():
                self.dismiss({"title": title, "project_id": int(pid)})

class AddNoteScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("[bold cyan]Add New Note[/bold cyan]", id="modal-title")
            yield Input(placeholder="Note Title", id="note-title")
            yield Input(placeholder="Content", id="note-content")
            with Horizontal(id="modal-buttons"):
                yield Button("Create", variant="success", id="submit")
                yield Button("Cancel", variant="error", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "submit":
            title = self.query_one("#note-title", Input).value
            content = self.query_one("#note-content", Input).value
            if title:
                self.dismiss({"title": title, "content": content})

class NexusTUI(App):
    CSS = """
    Screen {
        background: #10101c;
        color: #00ffff;
    }
    #header-container {
        height: auto;
        content-align: center middle;
        margin-top: 1;
        margin-bottom: 2;
    }
    #search {
        width: 60%;
        margin: 1 2;
        border: round #9d00ff;
    }
    #main-table {
        height: 1fr;
        margin: 1 2;
    }
    ModalScreen {
        align: center middle;
        background: $background 80%;
    }
    #modal-dialog {
        padding: 1 2;
        width: 60;
        height: auto;
        border: round #9d00ff;
        background: #1a1a2e;
    }
    #modal-title {
        content-align: center middle;
        margin-bottom: 1;
    }
    #modal-buttons {
        margin-top: 1;
        align: center middle;
    }
    Button {
        margin: 0 2;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "show_projects", "Projects"),
        ("t", "show_tasks", "Tasks"),
        ("n", "show_notes", "Notes"),
        ("ctrl+p", "add_project", "Add Project"),
        ("ctrl+t", "add_task", "Add Task"),
        ("ctrl+n", "add_note", "Add Note"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(NexusHeader(), id="header-container")
        yield Input(placeholder="Search NEXUS...", id="search")
        yield DataTable(id="main-table")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "NEXUS Core TUI"
        self.theme = "textual-dark"
        self.current_view = "projects"
        self.action_show_projects()

    def refresh_current_view(self) -> None:
        if self.current_view == "projects":
            self.action_show_projects()
        elif self.current_view == "tasks":
            self.action_show_tasks()
        elif self.current_view == "notes":
            self.action_show_notes()

    def action_show_projects(self) -> None:
        self.current_view = "projects"
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Project Title", "Status")
        
        try:
            response = requests.get(f"{config.api_url}/api/projects", headers=get_headers())
            if response.status_code == 200:
                projects = response.json()
                for p in projects:
                    status = "✅ Completed" if p.get("status") == "completed" else "⏳ Pending"
                    table.add_row(str(p["id"]), p["title"], status)
        except Exception:
            table.add_row("ERR", "Could not connect to Core API", "ERROR")

    def action_show_tasks(self) -> None:
        self.current_view = "tasks"
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Task Title", "Project ID", "Status")
        
        try:
            response = requests.get(f"{config.api_url}/api/tasks", headers=get_headers())
            if response.status_code == 200:
                tasks = response.json()
                for t in tasks:
                    status = "✅ Done" if t.get("is_completed") else "⏳ Pending"
                    table.add_row(str(t["id"]), t["title"], str(t.get("project_id", "-")), status)
        except Exception:
            table.add_row("ERR", "Could not connect to Core API", "-", "ERROR")

    def action_show_notes(self) -> None:
        self.current_view = "notes"
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Note Title", "Content Preview")
        
        try:
            response = requests.get(f"{config.api_url}/api/notes", headers=get_headers())
            if response.status_code == 200:
                notes = response.json()
                for n in notes:
                    preview = (n.get("content") or "")[:50] + "..."
                    table.add_row(str(n["id"]), n["title"], preview)
        except Exception:
            table.add_row("ERR", "Could not connect to Core API", "ERROR")

    def action_add_project(self) -> None:
        def check_result(result):
            if result:
                try:
                    requests.post(f"{config.api_url}/api/projects", json=result, headers=get_headers())
                    self.refresh_current_view()
                except:
                    pass
        self.push_screen(AddProjectScreen(), check_result)

    def action_add_task(self) -> None:
        def check_result(result):
            if result:
                try:
                    requests.post(f"{config.api_url}/api/tasks", json=result, headers=get_headers())
                    self.refresh_current_view()
                except:
                    pass
        self.push_screen(AddTaskScreen(), check_result)

    def action_add_note(self) -> None:
        def check_result(result):
            if result:
                try:
                    requests.post(f"{config.api_url}/api/notes", json=result, headers=get_headers())
                    self.refresh_current_view()
                except:
                    pass
        self.push_screen(AddNoteScreen(), check_result)

if __name__ == "__main__":
    app = NexusTUI()
    app.run()
