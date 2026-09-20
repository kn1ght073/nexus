import warnings
warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")
import requests
from textual import on
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

class ChangeStatusScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("[bold cyan]Change Status[/bold cyan]", id="modal-title")
            with Horizontal(classes="modal-buttons"):
                yield Button("Pending ⏳", variant="warning", id="pending")
                yield Button("In Progress 🔄", variant="primary", id="in_progress")
                yield Button("Completed ✅", variant="success", id="completed")
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", variant="error", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        else:
            self.dismiss(event.button.id)

class SettingsScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("[bold cyan]TUI Settings[/bold cyan]", id="modal-title")
            yield Label("Select Theme:", id="theme-label")
            with Horizontal(classes="modal-buttons"):
                yield Button("Synthwave", variant="primary", id="textual-dark")
                yield Button("Light Mode", variant="warning", id="textual-light")
            with Horizontal(classes="modal-buttons"):
                yield Button("Close", variant="error", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        else:
            self.dismiss(event.button.id)

class AddProjectScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("[bold cyan]Add New Project[/bold cyan]", id="modal-title")
            yield Input(placeholder="Project Title", id="project-title")
            yield Input(placeholder="Description (optional)", id="project-desc")
            with Horizontal(classes="modal-buttons"):
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
            with Horizontal(classes="modal-buttons"):
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
            with Horizontal(classes="modal-buttons"):
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

class SearchScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("[bold cyan]Search Device Files[/bold cyan]", id="modal-title")
            yield Input(placeholder="Search Query...", id="search-query")
            with Horizontal(classes="modal-buttons"):
                yield Button("Search", variant="success", id="submit")
                yield Button("Cancel", variant="error", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "submit":
            query = self.query_one("#search-query", Input).value
            if query:
                self.dismiss(query)

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
    #theme-label {
        content-align: center middle;
        margin-top: 1;
    }
    .modal-buttons {
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
        ("f", "show_files", "Files"),
        ("s", "show_search", "Search"),
        ("P", "add_project", "Add Project"),
        ("T", "add_task", "Add Task"),
        ("N", "add_note", "Add Note"),
        ("ctrl+s", "command_palette", "Palette"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(NexusHeader(), id="header-container")
        yield Input(placeholder="Search NEXUS...", id="search")
        yield DataTable(id="main-table", cursor_type="row")
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
        elif self.current_view == "files":
            self.action_show_files()

    def format_status(self, status: str) -> str:
        if status == "completed": return "✅ Completed"
        if status == "in_progress": return "🔄 In Progress"
        return "⏳ Pending"

    def action_show_projects(self) -> None:
        table = self.query_one(DataTable)
        if self.current_view != "projects" or not table.columns:
            table.clear(columns=True)
            table.add_columns("ID", "Project Title", "Status")
        else:
            table.clear()
        self.current_view = "projects"
        
        try:
            response = requests.get(f"{config.api_url}/api/projects", headers=get_headers())
            if response.status_code == 200:
                projects = response.json()
                for p in projects:
                    table.add_row(str(p["id"]), p["title"], self.format_status(p.get("status", "pending")), key=str(p["id"]))
        except Exception:
            table.add_row("ERR", "Could not connect to Core API", "ERROR", key="ERR")

    def action_show_tasks(self) -> None:
        table = self.query_one(DataTable)
        if self.current_view != "tasks" or not table.columns:
            table.clear(columns=True)
            table.add_columns("ID", "Task Title", "Project ID", "Status")
        else:
            table.clear()
        self.current_view = "tasks"
        
        try:
            response = requests.get(f"{config.api_url}/api/tasks", headers=get_headers())
            if response.status_code == 200:
                tasks = response.json()
                for t in tasks:
                    table.add_row(str(t["id"]), t["title"], str(t.get("project_id", "-")), self.format_status(t.get("status", "pending")), key=str(t["id"]))
        except Exception:
            table.add_row("ERR", "Could not connect to Core API", "-", "ERROR", key="ERR")

    def action_show_notes(self) -> None:
        table = self.query_one(DataTable)
        if self.current_view != "notes" or not table.columns:
            table.clear(columns=True)
            table.add_columns("ID", "Note Title", "Content Preview")
        else:
            table.clear()
        self.current_view = "notes"
        
        try:
            response = requests.get(f"{config.api_url}/api/notes", headers=get_headers())
            if response.status_code == 200:
                notes = response.json()
                for n in notes:
                    preview = (n.get("content") or "")[:50] + "..."
                    table.add_row(str(n["id"]), n["title"], preview, key=str(n["id"]))
        except Exception:
            table.add_row("ERR", "Could not connect to Core API", "ERROR", key="ERR")

    @on(DataTable.RowSelected)
    def handle_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key.value
        if row_key in ["ERR", "EMPTY"] or self.current_view in ["notes", "files", "search"]:
            return
            
        def check_result(result):
            if result:
                endpoint = "projects" if self.current_view == "projects" else "tasks"
                try:
                    requests.patch(
                        f"{config.api_url}/api/{endpoint}/{row_key}/status", 
                        json={"status": result}, 
                        headers=get_headers()
                    )
                    self.refresh_current_view()
                except:
                    pass

        self.push_screen(ChangeStatusScreen(), check_result)

    def action_settings(self) -> None:
        def check_result(result):
            if result:
                self.theme = result
        self.push_screen(SettingsScreen(), check_result)

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

    def action_show_files(self) -> None:
        table = self.query_one(DataTable)
        if self.current_view != "files" or not table.columns:
            table.clear(columns=True)
            table.add_columns("Type", "Name", "Size (bytes)")
        else:
            table.clear()
        self.current_view = "files"
        
        try:
            response = requests.get(f"{config.api_url}/api/files/browse", headers=get_headers())
            if response.status_code == 200:
                files = response.json()
                for f in files:
                    icon = "📁" if f["is_dir"] else "📄"
                    size_str = str(f["size"]) if not f["is_dir"] else "-"
                    table.add_row(icon, f["name"], size_str, key=f["path"])
        except Exception:
            table.add_row("ERR", "Could not connect to Core API", "ERROR", key="ERR")

    def action_show_search(self) -> None:
        def check_result(query):
            if query:
                self.perform_search(query)
        self.push_screen(SearchScreen(), check_result)

    def perform_search(self, query: str) -> None:
        table = self.query_one(DataTable)
        if self.current_view != "search" or not table.columns:
            table.clear(columns=True)
            table.add_columns("File Path", "Match Context")
        else:
            table.clear()
        self.current_view = "search"
        
        try:
            response = requests.get(f"{config.api_url}/api/files/search", params={"query": query}, headers=get_headers())
            if response.status_code == 200:
                results = response.json()
                if not results:
                    table.add_row("-", "No results found.", key="EMPTY")
                for r in results:
                    table.add_row(r["path"], r["match_context"], key=r["path"])
        except Exception:
            table.add_row("ERR", "Could not connect to Core API", key="ERR")

if __name__ == "__main__":
    app = NexusTUI()
    app.run()
