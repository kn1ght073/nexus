"""Files and Storage Explorer Widget for NEXUS Control Center.

Super File inspired dual-pane explorer featuring interactive breadcrumb navigation,
jailed directory trees, live file preview syntax inspection, and text search.
"""

from datetime import datetime
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DataTable, Input, Label, Static

from ...client import get_client
from ...config import load_config
from .context import ContextPanel


class FilesView(Static):
    """Storage & File Explorer with breadcrumbs, directory browser, and live file preview."""

    class FileAction(Message):
        def __init__(self, action_id: str, path: str) -> None:
            self.action_id = action_id
            self.path = path
            super().__init__()

    current_path: str = ""
    _files_cache: List[Dict[str, Any]] = []
    _files_by_key: Dict[str, Dict[str, Any]] = {}
    selected_file: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="files-container"):
            # Top Breadcrumbs and Search bar
            with Horizontal(classes="view-header-bar"):
                yield Label("📁 FILES & SOVEREIGN STORAGE", classes="view-title")
                with Horizontal(classes="header-actions"):
                    yield Input(placeholder="Search files or grep content... (Enter)", id="files-search-input")
                    yield Button("⬆ Up", id="btn-file-up", classes="btn-sm")
                    yield Button("🔄 Refresh", id="btn-file-refresh", classes="btn-sm")

            # Breadcrumbs path bar
            with Horizontal(id="files-breadcrumb-bar"):
                yield Label("Location: ", classes="breadcrumb-label")
                yield Label("storage roots / (default)", id="files-breadcrumb-path")

            # Dual-Pane Layout: Left = Files Table, Right = Live File Preview
            with Horizontal(id="files-dual-pane"):
                # Left Directory Pane
                with Vertical(id="files-list-pane"):
                    table = DataTable(id="files-table", cursor_type="row")
                    table.zebra_stripes = True
                    yield table

                # Right Preview Pane (Super File inspired)
                with Vertical(id="files-preview-pane", classes="details-box"):
                    yield Label("FILE PREVIEW & METADATA", classes="box-title")
                    yield Static("Select a file to inspect metadata and live content preview.", id="files-preview-static")
                    with Horizontal(id="files-action-buttons"):
                        yield Button("📋 Copy Path", id="btn-copy-path", classes="btn-sm")
                        yield Button("🔍 Deep Search", id="btn-deep-search", classes="btn-sm")

    def on_mount(self) -> None:
        table = self.query_one("#files-table", DataTable)
        table.add_columns("Type", "Name", "Size", "Path")
        self.browse_directory(None)

    def browse_directory(self, target_path: Optional[str] = None) -> None:
        self.run_worker(lambda: self._fetch_directory(target_path), thread=True)

    def _fetch_directory(self, target_path: Optional[str]) -> None:
        client = get_client()
        params = {"path": target_path} if target_path else {}
        files = []
        try:
            r = client.get("/api/files/browse", params=params, timeout=4)
            if r.status_code == 200:
                files = r.json()
        except Exception:
            pass

        self.app.call_from_thread(self._render_directory, target_path or "", files)

    def _render_directory(self, path_str: str, files: List[Dict[str, Any]]) -> None:
        if not self.is_mounted:
            return
        self.current_path = path_str
        self._files_cache = files
        self._files_by_key.clear()

        try:
            bc = self.query_one("#files-breadcrumb-path", Label)
            bc.update(f"storage roots / {path_str}" if path_str else "storage roots / (root)")
            table = self.query_one("#files-table", DataTable)
        except Exception:
            return
        table.clear()

        first_key = None
        for f in files:
            is_dir = f.get("is_dir", False)
            icon = "📁 DIR" if is_dir else "📄 FILE"
            name = f.get("name", "Unknown")
            size_str = f"{f.get('size', 0):,} B" if not is_dir else "[dim]--[/dim]"
            p = f.get("path", name)

            key = f"{'dir' if is_dir else 'file'}:{p}"
            self._files_by_key[key] = f
            if first_key is None:
                first_key = key

            name_styled = f"[bold cyan]{name}/[/bold cyan]" if is_dir else name
            table.add_row(icon, name_styled, size_str, p, key=key)

        if not files:
            table.add_row("ℹ️", "[dim]Directory is empty or inaccessible[/dim]", "-", path_str or "-")
            self.query_one("#files-preview-static", Static).update("[dim]No files found in this storage directory.[/dim]")
        elif first_key and first_key in self._files_by_key:
            self._display_file_preview(self._files_by_key[first_key])

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value in self._files_by_key:
            f = self._files_by_key[event.row_key.value]
            self._display_file_preview(f)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value in self._files_by_key:
            f = self._files_by_key[event.row_key.value]
            if f.get("is_dir"):
                self.browse_directory(f.get("path"))

    def _display_file_preview(self, f: Dict[str, Any]) -> None:
        self.selected_file = f
        is_dir = f.get("is_dir", False)
        name = f.get("name", "")
        p = f.get("path", "")
        size = f.get("size", 0)

        lines = [
            f"[bold cyan]{'📁 ' if is_dir else '📄 '}{name}[/bold cyan]",
            f"[dim]Path: {p}[/dim]",
            f"[bold]Type:[/bold] {'Directory' if is_dir else 'Regular File'}",
            f"[bold]Size:[/bold] {size:,} bytes" if not is_dir else "[bold]Size:[/bold] Directory",
            "",
        ]

        if is_dir:
            lines.append("[dim]Press Enter on this row to browse into this directory.[/dim]")
        else:
            lines.append("[bold]Content Preview:[/bold]")
            ext = os.path.splitext(name)[1].lower()
            if ext in (".txt", ".md", ".json", ".py", ".yaml", ".yml", ".toml", ".sh", ".env", ".cfg"):
                # Safe read of small files if local path exists
                preview_text = ""
                try:
                    if os.path.exists(p) and os.path.isfile(p):
                        with open(p, "r", encoding="utf-8", errors="replace") as pf:
                            preview_text = "".join(pf.readlines()[:20])
                except Exception:
                    pass

                if preview_text:
                    lines.append(f"[dim]{preview_text}[/dim]")
                else:
                    lines.append(f"[dim](Plaintext/Config file format: {ext})[/dim]")
            else:
                lines.append(f"[dim]Binary or unsupported preview format ({ext or 'raw'}).[/dim]")

        try:
            self.query_one("#files-preview-static", Static).update("\n".join(lines))
        except Exception:
            pass

        # Update context panel
        try:
            ctx = self.app.query_one(ContextPanel)
            ctx.update_resource(
                title=f"{'Directory' if is_dir else 'File'}: {name}",
                subtitle=f"{size:,} bytes — {p}",
                properties={
                    "Name": name,
                    "Type": "Directory" if is_dir else "File",
                    "Size": f"{size:,} B",
                    "Jailed Root": "Enforced (Safe)",
                },
                action_label="Copy Path" if not is_dir else "Browse Directory",
                action_id="files.action",
                action_data={"path": p, "is_dir": is_dir},
                help_text="Browse storage roots safely without exposing private system files.",
            )
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "files-search-input" and event.value.strip():
            q = event.value.strip()
            self.run_worker(lambda: self._search_files(q), thread=True)

    def _search_files(self, query: str) -> None:
        client = get_client()
        files = []
        try:
            r = client.get("/api/files/search", params={"q": query}, timeout=5)
            if r.status_code == 200:
                files = r.json()
        except Exception:
            pass
        self.app.call_from_thread(self._render_directory, f"search:{query}", files)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-file-refresh":
            self.browse_directory(self.current_path or None)
        elif btn_id == "btn-file-up":
            if self.current_path:
                parent = str(Path(self.current_path).parent)
                if parent in (".", "/"):
                    self.browse_directory(None)
                else:
                    self.browse_directory(parent)
            else:
                self.browse_directory(None)
        elif btn_id == "btn-copy-path" and self.selected_file:
            self.post_message(self.FileAction("copy_path", self.selected_file.get("path", "")))
        elif btn_id == "btn-deep-search":
            inp = self.query_one("#files-search-input", Input)
            if inp.value.strip():
                self._search_files(inp.value.strip())
