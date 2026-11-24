"""Local SQLite storage buffer for NEXUS CLI and TUI.

Provides immediate offline and control-plane resilience for projects, tasks,
and notes when the user is operating in standalone mode or connected to a
cloud control plane where workspace content endpoints (/api/projects,
/api/tasks, /api/notes) are not mounted.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

DB_DIR = Path.home() / ".nexus"
DB_PATH = DB_DIR / "local_store.db"


def _get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS local_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active',
                revision INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS local_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                project_id INTEGER,
                priority INTEGER DEFAULT 1,
                due_date TEXT,
                revision INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS local_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                project_id INTEGER,
                revision INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        # Seed default workspace if empty
        cur = conn.execute("SELECT COUNT(*) FROM local_projects")
        if cur.fetchone()[0] == 0:
            now = datetime.utcnow().isoformat()
            conn.execute(
                """
                INSERT INTO local_projects (title, description, status, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("Default Sovereign Workspace", "Primary local project container", "active", 1, now, now),
            )


# --- Projects ---

def list_local_projects() -> List[Dict[str, Any]]:
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT * FROM local_projects ORDER BY id ASC")
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def create_local_project(title: str, description: Optional[str] = "") -> Dict[str, Any]:
    conn = _get_connection()
    try:
        now = datetime.utcnow().isoformat()
        with conn:
            cur = conn.execute(
                """
                INSERT INTO local_projects (title, description, status, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, description or "", "active", 1, now, now),
            )
            proj_id = cur.lastrowid
            cur = conn.execute("SELECT * FROM local_projects WHERE id = ?", (proj_id,))
            return dict(cur.fetchone())
    finally:
        conn.close()


def delete_local_project(project_id: int) -> bool:
    conn = _get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM local_projects WHERE id = ?", (project_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


# --- Tasks ---

def list_local_tasks() -> List[Dict[str, Any]]:
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT * FROM local_tasks ORDER BY id ASC")
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def create_local_task(title: str, project_id: Optional[int] = None, description: Optional[str] = None) -> Dict[str, Any]:
    conn = _get_connection()
    try:
        now = datetime.utcnow().isoformat()
        with conn:
            cur = conn.execute(
                """
                INSERT INTO local_tasks (title, description, status, project_id, priority, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title, description, "pending", project_id, 1, 1, now, now),
            )
            task_id = cur.lastrowid
            cur = conn.execute("SELECT * FROM local_tasks WHERE id = ?", (task_id,))
            return dict(cur.fetchone())
    finally:
        conn.close()


def update_local_task_status(task_id: int, status: str = "completed") -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    try:
        now = datetime.utcnow().isoformat()
        with conn:
            conn.execute(
                "UPDATE local_tasks SET status = ?, updated_at = ?, revision = revision + 1 WHERE id = ?",
                (status, now, task_id),
            )
            cur = conn.execute("SELECT * FROM local_tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def delete_local_task(task_id: int) -> bool:
    conn = _get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM local_tasks WHERE id = ?", (task_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


# --- Notes ---

def list_local_notes() -> List[Dict[str, Any]]:
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT * FROM local_notes ORDER BY id ASC")
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def create_local_note(title: str, content: str, tags: Optional[str] = None, project_id: Optional[int] = None) -> Dict[str, Any]:
    conn = _get_connection()
    try:
        now = datetime.utcnow().isoformat()
        with conn:
            cur = conn.execute(
                """
                INSERT INTO local_notes (title, content, tags, project_id, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (title, content, tags or "", project_id, 1, now, now),
            )
            note_id = cur.lastrowid
            cur = conn.execute("SELECT * FROM local_notes WHERE id = ?", (note_id,))
            return dict(cur.fetchone())
    finally:
        conn.close()


def delete_local_note(note_id: int) -> bool:
    conn = _get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM local_notes WHERE id = ?", (note_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


# --- Storage Roots & File Browsing ---

STORAGE_ROOT = Path.home() / ".nexus" / "storage"


def ensure_storage_root() -> Path:
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    # Seed default sample files if empty
    docs_dir = STORAGE_ROOT / "documents"
    docs_dir.mkdir(exist_ok=True)
    welcome_file = docs_dir / "welcome_to_nexus.txt"
    if not welcome_file.exists():
        welcome_file.write_text(
            "Welcome to NEXUS Sovereign Storage!\nThis directory is jailed inside ~/.nexus/storage.\n"
            "All your local sovereign files, scripts, and exports are preserved here.\n",
            encoding="utf-8",
        )
    projects_dir = STORAGE_ROOT / "projects"
    projects_dir.mkdir(exist_ok=True)
    sample_spec = projects_dir / "architecture_spec.json"
    if not sample_spec.exists():
        sample_spec.write_text(
            json.dumps({"ecosystem": "NEXUS", "storage": "sovereign", "version": "0.2.0"}, indent=2),
            encoding="utf-8",
        )
    return STORAGE_ROOT


def list_local_storage_files(relative_path: Optional[str] = None) -> List[Dict[str, Any]]:
    root = ensure_storage_root()
    target_dir = root
    if relative_path:
        clean_rel = relative_path.strip().lstrip("/")
        candidate = (root / clean_rel).resolve()
        if candidate.is_relative_to(root) and candidate.is_dir():
            target_dir = candidate

    files = []
    try:
        for entry in sorted(target_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            try:
                rel = entry.relative_to(root).as_posix()
                is_dir = entry.is_dir()
                size = entry.stat().st_size if not is_dir else 4096
                files.append({
                    "name": entry.name,
                    "path": rel,
                    "is_dir": is_dir,
                    "size": size,
                    "modified_at": datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
                })
            except Exception:
                continue
    except Exception:
        pass
    return files


def search_local_storage_files(query: str) -> List[Dict[str, Any]]:
    root = ensure_storage_root()
    q = query.lower()
    results = []
    try:
        for entry in root.rglob("*"):
            if q in entry.name.lower():
                try:
                    rel = entry.relative_to(root).as_posix()
                    is_dir = entry.is_dir()
                    size = entry.stat().st_size if not is_dir else 4096
                    results.append({
                        "name": entry.name,
                        "path": rel,
                        "is_dir": is_dir,
                        "size": size,
                        "modified_at": datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return results
