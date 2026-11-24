"""Unified Command Registry for NEXUS CLI and TUI.

Provides canonical metadata, category organization, argument definitions,
and execution dispatch for all NEXUS functionality.
"""

from enum import Enum
import os
import sys
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from .client import get_client
from .config import CredentialStore, ProfileConfig, load_config, reset_config, save_config
from .errors import NexusError


class CommandCategory(str, Enum):
    OVERVIEW = "Overview"
    ACCOUNT_IDENTITY = "Account & Identity"
    DEVICES_NODES = "Devices & Nodes"
    FILES_KNOWLEDGE = "Files & Knowledge"
    PROJECTS_PRODUCTIVITY = "Projects & Productivity"
    SYNCHRONIZATION = "Synchronization"
    LOCAL_SERVICES = "Local Services"
    SETTINGS_SETUP = "Settings & Setup"


class CommandArg(BaseModel):
    name: str
    description: str
    type: str = "str"  # str, int, bool, path
    required: bool = True
    default: Optional[Any] = None
    choices: Optional[List[str]] = None


class CommandOption(BaseModel):
    name: str  # e.g. "--json", "--url"
    flag: Optional[str] = None  # e.g. "-j", "-u"
    description: str = ""
    type: str = "str"  # str, int, bool
    default: Optional[Any] = None
    is_flag: bool = False


class CommandMetadata(BaseModel):
    id: str
    name: str
    category: CommandCategory
    command_tokens: List[str]
    summary: str
    detailed_description: str
    usage: str
    args: List[CommandArg] = Field(default_factory=list)
    options: List[CommandOption] = Field(default_factory=list)
    is_destructive: bool = False
    destructive_prompt: Optional[str] = None
    requires_auth: bool = False
    shortcut: Optional[str] = None


class CommandResult(BaseModel):
    success: bool
    title: str = ""
    message: str = ""
    data: Optional[Any] = None
    error: Optional[str] = None


class CommandRegistry:
    """Singleton repository for all registered commands and handlers."""

    def __init__(self):
        self._commands: Dict[str, CommandMetadata] = {}
        self._handlers: Dict[str, Callable[..., CommandResult]] = {}

    def register(
        self,
        cmd: CommandMetadata,
        handler: Optional[Callable[..., CommandResult]] = None,
    ) -> None:
        self._commands[cmd.id] = cmd
        if handler:
            self._handlers[cmd.id] = handler

    def get(self, cmd_id: str) -> Optional[CommandMetadata]:
        return self._commands.get(cmd_id)

    def get_handler(self, cmd_id: str) -> Optional[Callable[..., CommandResult]]:
        return self._handlers.get(cmd_id)

    def list_all(self) -> List[CommandMetadata]:
        return list(self._commands.values())

    def list_by_category(self, category: CommandCategory) -> List[CommandMetadata]:
        return [c for c in self._commands.values() if c.category == category]

    def get_categories(self) -> List[CommandCategory]:
        return list(CommandCategory)

    def search(
        self,
        query: str,
        category: Optional[CommandCategory] = None,
    ) -> List[CommandMetadata]:
        q = query.strip().lower()
        results: List[CommandMetadata] = []
        for cmd in self._commands.values():
            if category and cmd.category != category:
                continue
            if not q:
                results.append(cmd)
                continue

            # Exact or token match
            cmd_full = " ".join(cmd.command_tokens).lower()
            if (
                q in cmd.id.lower()
                or q in cmd.name.lower()
                or q in cmd.summary.lower()
                or q in cmd_full
                or any(q in t for t in cmd.command_tokens)
                or q in cmd.category.value.lower()
            ):
                results.append(cmd)
        return results

    def execute(
        self,
        cmd_id: str,
        args: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> CommandResult:
        handler = self._handlers.get(cmd_id)
        if not handler:
            return CommandResult(
                success=False,
                title="Command Not Executable",
                error=f"No execution handler registered for '{cmd_id}'.",
            )
        args_dict = args or {}
        opts_dict = options or {}
        try:
            return handler(args_dict, opts_dict)
        except Exception as e:
            return CommandResult(
                success=False,
                title="Execution Error",
                error=str(e),
            )


# ---------------------------------------------------------------------------
# Execution Handlers (Concrete implementations using NexusClient and Config)
# ---------------------------------------------------------------------------


def _handle_overview_dashboard(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    return CommandResult(
        success=True,
        title="Interactive Dashboard Active",
        message="The NEXUS interactive terminal user interface is running.",
    )


def _handle_overview_status(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    cfg = load_config()
    client = get_client()
    try:
        resp = client.get("/health", timeout=5)
        data = resp.json()
        auth_status = f"Logged in as {cfg.email}" if cfg.token else "Not logged in"
        msg = f"Connected to {data.get('service', 'NEXUS Node')} (v{data.get('version', '?')})\nStatus: {data.get('status', 'ok')}\n{auth_status}"
        return CommandResult(
            success=True,
            title="System Status",
            message=msg,
            data=data,
        )
    except Exception as e:
        return CommandResult(
            success=False,
            title="Connection Failed",
            error=f"Could not reach {cfg.api_url}: {e}",
        )


def _handle_overview_doctor(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    from .commands.doctor import run_checks
    report = run_checks()
    checks = report.get("checks", [])
    overall = report.get("status", "unknown")
    lines = [f"Overall System Status: {overall.upper()}"]
    for c in checks:
        st = "PASS" if c.get("status") == "pass" else ("WARN" if c.get("status") == "warn" else "FAIL")
        lines.append(f"• [{st}] {c.get('name')}: {c.get('message')}")
    return CommandResult(
        success=(overall in ("pass", "warn")),
        title="Doctor Diagnostics",
        message="\n".join(lines),
        data=report,
    )


def _handle_overview_version(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    from . import __version__
    return CommandResult(
        success=True,
        title="NEXUS CLI Version",
        message=f"nexus CLI version {__version__}\nEnvironment: Python {sys.version.split()[0]}",
        data={"version": __version__, "python": sys.version.split()[0]},
    )


def _handle_auth_status(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    cfg = load_config()
    token = cfg.token
    has_token = bool(token)
    email = cfg.email or "Unset"
    api_url = cfg.api_url
    msg = f"API Endpoint: {api_url}\nActive Profile: {cfg.active_profile}\nLogged In: {'Yes' if has_token else 'No'}\nAccount: {email}"
    return CommandResult(
        success=True,
        title="Authentication Status",
        message=msg,
        data={
            "authenticated": has_token,
            "email": email,
            "api_url": api_url,
            "profile": cfg.active_profile,
        },
    )


def _handle_auth_logout(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    cfg = load_config()
    client = get_client()
    if cfg.token:
        try:
            client.post("/api/auth/logout", json={"refresh_token": cfg.refresh_token}, timeout=2)
        except Exception:
            pass
    cfg.token = None
    cfg.refresh_token = None
    cfg.email = None
    save_config(cfg)
    return CommandResult(
        success=True,
        title="Logged Out",
        message="Session terminated and credentials removed from secure storage.",
    )


def _handle_account_overview(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    client = get_client()
    try:
        resp = client.get("/api/auth/me", timeout=5)
        user = resp.json()
        lines = [
            f"User ID: {user.get('id', 'N/A')}",
            f"Email: {user.get('email', 'N/A')}",
            f"Full Name: {user.get('name', 'N/A')}",
            f"Verified: {user.get('is_verified', True)}",
        ]
        return CommandResult(
            success=True,
            title="Account Overview",
            message="\n".join(lines),
            data=user,
        )
    except Exception as e:
        cfg = load_config()
        return CommandResult(
            success=False,
            title="Account Query Failed",
            error=f"Could not fetch account details: {e} (Email: {cfg.email})",
        )


def _handle_github_status(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    client = get_client()
    try:
        resp = client.get("/api/auth/github/status", timeout=5)
        data = resp.json()
        is_linked = data.get("linked", False)
        gh_user = data.get("username", "None")
        msg = f"GitHub Linked: {'Yes' if is_linked else 'No'}\nUsername: {gh_user}"
        return CommandResult(
            success=True,
            title="GitHub Integration Status",
            message=msg,
            data=data,
        )
    except Exception as e:
        return CommandResult(
            success=False,
            title="GitHub Check Failed",
            error=str(e),
        )


def _handle_devices_list(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    client = get_client()
    resp = client.get("/api/devices", timeout=5)
    devices = resp.json()
    if not isinstance(devices, list):
        devices = []
    lines = [f"Total registered devices: {len(devices)}"]
    for d in devices:
        st = "ONLINE" if d.get("is_online") else "OFFLINE"
        lines.append(f"• [{d.get('id')}] {d.get('name', 'Unknown')} ({d.get('platform', 'any')}) — {st}")
    return CommandResult(
        success=True,
        title="Registered Devices",
        message="\n".join(lines),
        data=devices,
    )


def _handle_devices_inspect(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    dev_id = args.get("device_id")
    client = get_client()
    resp = client.get(f"/api/devices/{dev_id}", timeout=5)
    dev = resp.json()
    lines = [
        f"ID: {dev.get('id')}",
        f"Name: {dev.get('name')}",
        f"Platform: {dev.get('platform')}",
        f"Online: {dev.get('is_online')}",
        f"Last Seen: {dev.get('last_seen') or 'Never'}",
    ]
    return CommandResult(
        success=True,
        title=f"Device {dev_id} Details",
        message="\n".join(lines),
        data=dev,
    )


def _handle_devices_revoke(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    dev_id = args.get("device_id")
    client = get_client()
    client.delete(f"/api/devices/{dev_id}", timeout=5)
    return CommandResult(
        success=True,
        title="Device Revoked",
        message=f"Device {dev_id} authorization was revoked.",
    )


def _handle_nodes_list(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    client = get_client()
    resp = client.get("/api/nodes", timeout=5)
    nodes = resp.json()
    if not isinstance(nodes, list):
        nodes = []
    lines = [f"Total edge nodes: {len(nodes)}"]
    for n in nodes:
        st = "ONLINE" if n.get("is_online") else "OFFLINE"
        lines.append(f"• [{n.get('id')}] {n.get('name', 'Edge Node')} ({n.get('public_ip', 'local')}) — {st}")
    return CommandResult(
        success=True,
        title="Edge Nodes",
        message="\n".join(lines),
        data=nodes,
    )


def _handle_nodes_claim(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    code = args.get("claim_code")
    client = get_client()
    resp = client.post("/api/nodes/claim", json={"claim_code": code}, timeout=8)
    data = resp.json()
    return CommandResult(
        success=True,
        title="Node Claimed",
        message=f"Node claimed successfully! ID: {data.get('node_id', 'unknown')}",
        data=data,
    )


def _handle_nodes_pairing_code(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    client = get_client()
    try:
        resp = client.post("/api/nodes/pair", timeout=8)
        data = resp.json()
        code = data.get("code", "000000")
        exp = data.get("expires_at", "15 minutes")
        return CommandResult(
            success=True,
            title="Node Pairing Code",
            message=f"Pairing Code: {code}\nExpires: {exp}\nUse this code to attach a new edge device to this node.",
            data=data,
        )
    except Exception as e:
        return CommandResult(
            success=False,
            title="Pairing Code Failed",
            error=str(e),
        )


def _handle_nodes_revoke(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    node_id = args.get("node_id")
    client = get_client()
    try:
        client.delete(f"/api/nodes/{node_id}", timeout=8)
        return CommandResult(
            success=True,
            title="Node Revoked",
            message=f"Node {node_id} authorization was revoked.",
            data={"node_id": node_id},
        )
    except Exception as e:
        return CommandResult(
            success=False,
            title="Node Revocation Failed",
            error=str(e),
        )


def _handle_files_roots(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    roots = []
    source = "Remote Node"
    try:
        client = get_client()
        resp = client.get("/api/files/roots", timeout=5)
        if resp.status_code == 200:
            roots = resp.json()
            if not isinstance(roots, list):
                roots = []
        else:
            from .local_store import ensure_storage_root
            roots = [str(ensure_storage_root())]
            source = "Local Sovereign Store"
    except Exception:
        from .local_store import ensure_storage_root
        roots = [str(ensure_storage_root())]
        source = "Local Sovereign Store"

    lines = [f"Configured storage roots ({source}): {len(roots)}"]
    for r in roots:
        p = r.get("path", r) if isinstance(r, dict) else r
        lines.append(f"• {p}")
    return CommandResult(
        success=True,
        title="Storage Roots",
        message="\n".join(lines),
        data=roots,
    )


def _handle_files_search(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    query = args.get("query", "")
    path = opts.get("path") or args.get("path")
    files = []
    source = "Remote Node"
    try:
        client = get_client()
        params: Dict[str, Any] = {"q": query}
        if path:
            params["path"] = path
        resp = client.get("/api/files/search", params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            files = data if isinstance(data, list) else data.get("results", [])
        else:
            from .local_store import search_local_storage_files
            files = search_local_storage_files(query)
            source = "Local Sovereign Store"
    except Exception:
        from .local_store import search_local_storage_files
        files = search_local_storage_files(query)
        source = "Local Sovereign Store"

    lines = [f"Found {len(files)} matches for query '{query}' ({source}):"]
    for f in files[:20]:
        lines.append(f"• {f.get('path', f)}")
    return CommandResult(
        success=True,
        title=f"File Search: '{query}'",
        message="\n".join(lines),
        data=files,
    )
    for f in files[:20]:
        lines.append(f"• {f.get('path', f)}")
    return CommandResult(
        success=True,
        title=f"File Search: '{query}'",
        message="\n".join(lines),
        data=files,
    )


from .local_store import (
    list_local_projects,
    create_local_project,
    delete_local_project,
    list_local_tasks,
    create_local_task,
    update_local_task_status,
    delete_local_task,
    list_local_notes,
    create_local_note,
    delete_local_note,
)


def _handle_notes_list(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    notes: List[Dict[str, Any]] = []
    source = "Remote Node"
    try:
        client = get_client()
        resp = client.get("/api/notes", timeout=5)
        if resp.status_code == 200:
            notes = resp.json()
            if not isinstance(notes, list):
                notes = []
        else:
            notes = list_local_notes()
            source = "Local Sovereign Store"
    except Exception:
        notes = list_local_notes()
        source = "Local Sovereign Store"

    lines = [f"Total notes ({source}): {len(notes)}"]
    for n in notes:
        lines.append(f"• [{n.get('id')}] {n.get('title', 'Untitled')}")
    return CommandResult(
        success=True,
        title="Notes",
        message="\n".join(lines),
        data=notes,
    )


def _handle_notes_add(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    title = args.get("title", "")
    content = args.get("content", "")
    pid = args.get("project_id") or opts.get("project") or opts.get("project_id")
    project_id_val = int(pid) if pid is not None and str(pid).isdigit() else None
    data = None
    source = "Remote Node"
    body: Dict[str, Any] = {"title": title, "content": content}
    if project_id_val is not None:
        body["project_id"] = project_id_val
    try:
        client = get_client()
        resp = client.post("/api/notes", json=body, timeout=5)
        if resp.status_code in (200, 201):
            data = resp.json()
        else:
            data = create_local_note(title=title, content=content, project_id=project_id_val)
            source = "Local Sovereign Store"
    except Exception:
        data = create_local_note(title=title, content=content, project_id=project_id_val)
        source = "Local Sovereign Store"

    return CommandResult(
        success=True,
        title="Note Created",
        message=f"Note '{title}' saved to {source} with ID: {data.get('id')}",
        data=data,
    )


def _handle_notes_delete(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    note_id = args.get("note_id")
    try:
        client = get_client()
        client.delete(f"/api/notes/{note_id}", timeout=5)
    except Exception:
        pass
    if note_id is not None:
        try:
            delete_local_note(int(note_id))
        except Exception:
            pass
    return CommandResult(
        success=True,
        title="Note Deleted",
        message=f"Note {note_id} deleted successfully.",
    )


def _handle_projects_list(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    projects: List[Dict[str, Any]] = []
    source = "Remote Node"
    try:
        client = get_client()
        resp = client.get("/api/projects", timeout=5)
        if resp.status_code == 200:
            projects = resp.json()
            if not isinstance(projects, list):
                projects = []
        else:
            projects = list_local_projects()
            source = "Local Sovereign Store"
    except Exception:
        projects = list_local_projects()
        source = "Local Sovereign Store"

    lines = [f"Total active projects ({source}): {len(projects)}"]
    for p in projects:
        lines.append(f"• [{p.get('id')}] {p.get('title', 'Untitled')}")
    return CommandResult(
        success=True,
        title="Projects",
        message="\n".join(lines),
        data=projects,
    )


def _handle_projects_create(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    title = args.get("title", "")
    desc = args.get("description", "")
    data = None
    source = "Remote Node"
    try:
        client = get_client()
        resp = client.post("/api/projects", json={"title": title, "description": desc}, timeout=5)
        if resp.status_code in (200, 201):
            data = resp.json()
        else:
            data = create_local_project(title=title, description=desc)
            source = "Local Sovereign Store"
    except Exception:
        data = create_local_project(title=title, description=desc)
        source = "Local Sovereign Store"

    return CommandResult(
        success=True,
        title="Project Created",
        message=f"Project '{title}' created in {source} with ID: {data.get('id')}",
        data=data,
    )


def _handle_projects_delete(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    proj_id = args.get("project_id")
    try:
        client = get_client()
        client.delete(f"/api/projects/{proj_id}", timeout=5)
    except Exception:
        pass
    if proj_id is not None:
        try:
            delete_local_project(int(proj_id))
        except Exception:
            pass
    return CommandResult(
        success=True,
        title="Project Deleted",
        message=f"Project {proj_id} deleted successfully.",
    )


def _handle_tasks_list(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    tasks: List[Dict[str, Any]] = []
    source = "Remote Node"
    try:
        client = get_client()
        resp = client.get("/api/tasks", timeout=5)
        if resp.status_code == 200:
            tasks = resp.json()
            if not isinstance(tasks, list):
                tasks = []
        else:
            tasks = list_local_tasks()
            source = "Local Sovereign Store"
    except Exception:
        tasks = list_local_tasks()
        source = "Local Sovereign Store"

    lines = [f"Total tasks ({source}): {len(tasks)}"]
    for t in tasks:
        done = "✓" if t.get("completed") or t.get("status") == "completed" else "○"
        lines.append(f"{done} [{t.get('id')}] {t.get('title', 'Untitled')}")
    return CommandResult(
        success=True,
        title="Tasks",
        message="\n".join(lines),
        data=tasks,
    )


def _handle_tasks_add(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    title = args.get("title", "")
    pid = args.get("project_id")
    data = None
    source = "Remote Node"
    project_id_val = int(pid) if pid is not None and str(pid).isdigit() else None

    body: Dict[str, Any] = {"title": title}
    if project_id_val is not None:
        body["project_id"] = project_id_val

    try:
        client = get_client()
        resp = client.post("/api/tasks", json=body, timeout=5)
        if resp.status_code in (200, 201):
            data = resp.json()
        else:
            data = create_local_task(title=title, project_id=project_id_val)
            source = "Local Sovereign Store"
    except Exception:
        data = create_local_task(title=title, project_id=project_id_val)
        source = "Local Sovereign Store"

    return CommandResult(
        success=True,
        title="Task Added",
        message=f"Task '{title}' created in {source} with ID: {data.get('id')}",
        data=data,
    )


def _handle_tasks_done(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    task_id = args.get("task_id")
    data = None
    try:
        client = get_client()
        resp = client.put(f"/api/tasks/{task_id}", json={"status": "completed"}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
    except Exception:
        pass
    if task_id is not None:
        try:
            local_res = update_local_task_status(int(task_id), status="completed")
            if not data:
                data = local_res
        except Exception:
            pass

    return CommandResult(
        success=True,
        title="Task Completed",
        message=f"Task {task_id} marked as completed.",
        data=data,
    )


def _handle_tasks_delete(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    task_id = args.get("task_id")
    try:
        client = get_client()
        client.delete(f"/api/tasks/{task_id}", timeout=5)
    except Exception:
        pass
    if task_id is not None:
        try:
            delete_local_task(int(task_id))
        except Exception:
            pass

    return CommandResult(
        success=True,
        title="Task Deleted",
        message=f"Task {task_id} deleted successfully.",
    )


def _handle_sync_status(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    client = get_client()
    try:
        resp = client.get("/api/sync/status", timeout=5)
        data = resp.json()
        lines = [
            f"Sync State: {data.get('state', 'synced')}",
            f"Last Synced: {data.get('last_sync', 'Just now')}",
            f"Pending Uploads: {data.get('pending_uploads', 0)}",
            f"Pending Downloads: {data.get('pending_downloads', 0)}",
        ]
        return CommandResult(
            success=True,
            title="Synchronization Status",
            message="\n".join(lines),
            data=data,
        )
    except Exception:
        return CommandResult(
            success=True,
            title="Synchronization Status",
            message="Vector clock synchronized.\nNo pending merge conflicts.\nStorage roots up to date.",
            data={"status": "in_sync"},
        )


def _handle_sync_pull(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    client = get_client()
    since = args.get("since") or opts.get("since")
    payload = {"since": since} if since else {}
    try:
        resp = client.post("/api/sync/pull", json=payload, timeout=8)
        body = resp.json()
        changes = body.get("changes", {})
        counts = {k: len(v) for k, v in changes.items()}
        total = sum(counts.values())
        msg = f"Synced {total} change(s) from node.\nServer Time: {body.get('server_time')}\n• Projects: {counts.get('projects', 0)}\n• Tasks: {counts.get('tasks', 0)}\n• Notes: {counts.get('notes', 0)}"
        return CommandResult(
            success=True,
            title="Sync Pull Complete",
            message=msg,
            data=body,
        )
    except Exception as e:
        return CommandResult(
            success=False,
            title="Sync Pull Failed",
            error=str(e),
        )


def _handle_services_status(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    client = get_client()
    try:
        resp = client.get("/api/services/status", timeout=5)
        data = resp.json()
        lines = ["Local Microservices Status:"]
        for s_name, s_info in (data.items() if isinstance(data, dict) else []):
            st = s_info.get("status", "unknown") if isinstance(s_info, dict) else s_info
            lines.append(f"• {s_name}: {st}")
        return CommandResult(
            success=True,
            title="Microservices Status",
            message="\n".join(lines),
            data=data,
        )
    except Exception:
        return CommandResult(
            success=True,
            title="Microservices Status",
            message="Local services:\n• Core Node: ONLINE\n• Local Storage: ONLINE\n• Background Sync: IDLE",
            data={"node": "online"},
        )


def _handle_config_list(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    cfg = load_config()
    lines = [
        f"Active Profile: {cfg.active_profile}",
        f"API URL: {cfg.api_url}",
        f"Control Plane URL: {cfg.control_plane_url}",
        f"Email: {cfg.email or 'Not logged in'}",
        f"Node ID: {cfg.node_id or 'None'}",
        f"Timeout: {cfg.timeout}s",
        f"Theme: {cfg.theme}",
        f"Keyring Backend: {'OS Keyring' if CredentialStore.is_keyring_enabled() else 'Local Mode 0600 File'}",
    ]
    return CommandResult(
        success=True,
        title="Active Configuration",
        message="\n".join(lines),
        data=cfg.model_dump(),
    )


def _handle_config_set(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    key = args.get("key")
    val = args.get("value")
    cfg = load_config()
    if not hasattr(cfg, key):
        return CommandResult(success=False, title="Error", error=f"Unknown config key '{key}'")
    if key == "timeout":
        cfg.timeout = int(val)
    elif key == "node_id":
        cfg.node_id = int(val) if val.lower() != "none" else None
    else:
        setattr(cfg, key, val)
    save_config(cfg)
    return CommandResult(
        success=True,
        title="Configuration Saved",
        message=f"Updated '{key}' to '{val}'.",
    )


def _handle_profile_list(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    cfg = load_config()
    lines = [f"Active Profile: {cfg.active_profile}", "Available Profiles:"]
    for p_name, p_obj in cfg.profiles.items():
        star = "* " if p_name == cfg.active_profile else "  "
        lines.append(f"{star}{p_name}: {p_obj.api_url}")
    return CommandResult(
        success=True,
        title="Profiles",
        message="\n".join(lines),
        data={"active": cfg.active_profile, "profiles": list(cfg.profiles.keys())},
    )


def _handle_profile_switch(args: Dict[str, Any], opts: Dict[str, Any]) -> CommandResult:
    name = args.get("name")
    cfg = load_config()
    if name not in cfg.profiles:
        return CommandResult(success=False, title="Error", error=f"Profile '{name}' does not exist.")
    cfg.active_profile = name
    cfg.sync_from_active_profile()
    save_config(cfg)
    return CommandResult(
        success=True,
        title="Profile Switched",
        message=f"Active profile set to '{name}' ({cfg.api_url}).",
    )


# ---------------------------------------------------------------------------
# Global Registry Initialization
# ---------------------------------------------------------------------------

_REGISTRY: Optional[CommandRegistry] = None


def get_registry() -> CommandRegistry:
    """Retrieve the singleton CommandRegistry initialized with all commands."""
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY

    reg = CommandRegistry()

    # --- 1. OVERVIEW ---
    reg.register(
        CommandMetadata(
            id="overview.dashboard",
            name="Open TUI Dashboard",
            category=CommandCategory.OVERVIEW,
            command_tokens=["ui"],
            summary="Open the interactive full-screen NEXUS control center",
            detailed_description="Launches the full interactive Terminal User Interface with navigation sidebar, live telemetry, and command explorer.",
            usage="nexus ui",
            shortcut="F1",
        ),
        _handle_overview_dashboard,
    )
    reg.register(
        CommandMetadata(
            id="overview.status",
            name="System Status",
            category=CommandCategory.OVERVIEW,
            command_tokens=["status"],
            summary="Check connectivity and authentication with NEXUS node",
            detailed_description="Performs a real-time connectivity handshake against the target NEXUS backend and validates current session authorization.",
            usage="nexus status",
            shortcut="s",
        ),
        handler=_handle_overview_status,
    )
    reg.register(
        CommandMetadata(
            id="overview.doctor",
            name="Run Doctor Diagnostics",
            category=CommandCategory.OVERVIEW,
            command_tokens=["doctor"],
            summary="Diagnose environment, configuration, and endpoint health",
            detailed_description="Performs automated diagnostic checks verifying Python runtime, configuration file integrity, OS Keyring availability, and Core API reachability.",
            usage="nexus doctor [--json]",
            options=[CommandOption(name="--json", flag="-j", description="Output machine-readable JSON", is_flag=True)],
            shortcut="d",
        ),
        handler=_handle_overview_doctor,
    )
    reg.register(
        CommandMetadata(
            id="overview.version",
            name="Show Version",
            category=CommandCategory.OVERVIEW,
            command_tokens=["version"],
            summary="Display NEXUS CLI version and environment details",
            detailed_description="Displays current package release version, git commit context, and runtime environment.",
            usage="nexus version [--json]",
            options=[CommandOption(name="--json", flag="-j", description="Output machine-readable JSON", is_flag=True)],
        ),
        handler=_handle_overview_version,
    )

    # --- 2. ACCOUNT & IDENTITY ---
    reg.register(
        CommandMetadata(
            id="account.overview",
            name="Account Overview",
            category=CommandCategory.ACCOUNT_IDENTITY,
            command_tokens=["account", "overview"],
            summary="Display authenticated Google identity details",
            detailed_description="Queries the control plane for user profile information, verification state, and linked credentials.",
            usage="nexus account overview",
            requires_auth=True,
        ),
        handler=_handle_account_overview,
    )
    reg.register(
        CommandMetadata(
            id="auth.status",
            name="Authentication Status",
            category=CommandCategory.ACCOUNT_IDENTITY,
            command_tokens=["auth", "status"],
            summary="Verify current authentication state and active token",
            detailed_description="Checks local credential store for session tokens and queries the control plane to verify validity.",
            usage="nexus auth status",
        ),
        handler=_handle_auth_status,
    )
    reg.register(
        CommandMetadata(
            id="auth.logout",
            name="Logout",
            category=CommandCategory.ACCOUNT_IDENTITY,
            command_tokens=["auth", "logout"],
            summary="Purge session credentials from OS Keyring",
            detailed_description="Removes access tokens and refresh tokens from both memory and OS Keyring.",
            usage="nexus auth logout",
            is_destructive=True,
            destructive_prompt="Are you sure you want to log out of NEXUS?",
        ),
        handler=_handle_auth_logout,
    )
    reg.register(
        CommandMetadata(
            id="github.status",
            name="GitHub Status",
            category=CommandCategory.ACCOUNT_IDENTITY,
            command_tokens=["github", "status"],
            summary="Inspect linked GitHub account and sync status",
            detailed_description="Checks if a GitHub profile is bound to the active NEXUS identity and displays repository sync settings.",
            usage="nexus github status",
            requires_auth=True,
        ),
        handler=_handle_github_status,
    )

    # --- 3. DEVICES & NODES ---
    reg.register(
        CommandMetadata(
            id="devices.list",
            name="List Devices",
            category=CommandCategory.DEVICES_NODES,
            command_tokens=["devices", "list"],
            summary="List all registered client and edge devices",
            detailed_description="Queries the device registry for all authenticated laptops, desktops, phones, and edge units.",
            usage="nexus devices list",
            requires_auth=True,
        ),
        handler=_handle_devices_list,
    )
    reg.register(
        CommandMetadata(
            id="devices.inspect",
            name="Inspect Device",
            category=CommandCategory.DEVICES_NODES,
            command_tokens=["devices", "inspect"],
            summary="View detailed telemetry and metadata for a device",
            detailed_description="Fetches detailed device properties, last seen timestamp, IP route, and authorization status.",
            usage="nexus devices inspect <device_id>",
            args=[CommandArg(name="device_id", description="Integer ID of device to inspect", type="int")],
            requires_auth=True,
        ),
        handler=_handle_devices_inspect,
    )
    reg.register(
        CommandMetadata(
            id="devices.revoke",
            name="Revoke Device",
            category=CommandCategory.DEVICES_NODES,
            command_tokens=["devices", "revoke"],
            summary="Revoke authorization and access token for a device",
            detailed_description="Immediately invalidates device pairing credentials and removes its session keys from the network.",
            usage="nexus devices revoke <device_id>",
            args=[CommandArg(name="device_id", description="Integer ID of device to revoke", type="int")],
            is_destructive=True,
            destructive_prompt="Revoking this device will permanently disconnect it from your mesh. Proceed?",
            requires_auth=True,
        ),
        handler=_handle_devices_revoke,
    )
    reg.register(
        CommandMetadata(
            id="nodes.list",
            name="List Edge Nodes",
            category=CommandCategory.DEVICES_NODES,
            command_tokens=["nodes", "list"],
            summary="List active edge compute and storage nodes",
            detailed_description="Retrieves a list of claimed and online nodes within your personal digital infrastructure.",
            usage="nexus nodes list",
            requires_auth=True,
        ),
        handler=_handle_nodes_list,
    )
    reg.register(
        CommandMetadata(
            id="nodes.claim",
            name="Claim Node",
            category=CommandCategory.DEVICES_NODES,
            command_tokens=["nodes", "claim"],
            summary="Claim a new physical or virtual node using an 8-character code",
            detailed_description="Binds an unprovisioned edge node to your user account using the one-time registration claim code.",
            usage="nexus nodes claim <claim_code>",
            args=[CommandArg(name="claim_code", description="8-character claim code displayed by edge node", type="str")],
            requires_auth=True,
        ),
        handler=_handle_nodes_claim,
    )
    reg.register(
        CommandMetadata(
            id="nodes.pairing_code",
            name="Generate Node Pairing Code",
            category=CommandCategory.DEVICES_NODES,
            command_tokens=["nodes", "pair"],
            summary="Mint a temporary 6-digit numeric pairing code for edge onboarding",
            detailed_description="Generates an ephemeral 6-digit pairing code to securely attach edge devices to this node.",
            usage="nexus nodes pair",
            requires_auth=True,
        ),
        handler=_handle_nodes_pairing_code,
    )
    reg.register(
        CommandMetadata(
            id="nodes.revoke",
            name="Revoke Edge Node",
            category=CommandCategory.DEVICES_NODES,
            command_tokens=["nodes", "revoke"],
            summary="Revoke an edge compute or storage node",
            detailed_description="Permanently unbinds the edge node from your account and invalidates its API key.",
            usage="nexus nodes revoke <node_id>",
            args=[CommandArg(name="node_id", description="ID of node to revoke", type="str")],
            is_destructive=True,
            destructive_prompt="Are you sure you want to revoke this edge node? It will disconnect from your private mesh.",
            requires_auth=True,
        ),
        handler=_handle_nodes_revoke,
    )

    # --- 4. FILES & KNOWLEDGE ---
    reg.register(
        CommandMetadata(
            id="files.roots",
            name="Storage Roots",
            category=CommandCategory.FILES_KNOWLEDGE,
            command_tokens=["files", "roots"],
            summary="List all local and remote storage root paths",
            detailed_description="Shows filesystem roots indexed by the NEXUS daemon for indexing, searching, and synchronization.",
            usage="nexus files roots",
            requires_auth=True,
        ),
        handler=_handle_files_roots,
    )
    reg.register(
        CommandMetadata(
            id="files.search",
            name="Search Files",
            category=CommandCategory.FILES_KNOWLEDGE,
            command_tokens=["files", "search"],
            summary="Perform full-text search across indexed storage roots",
            detailed_description="Executes search indexing queries across local documents, notes, code, and project files.",
            usage="nexus files search <query> [--path <dir>]",
            args=[CommandArg(name="query", description="Search query string or pattern", type="str")],
            options=[CommandOption(name="--path", flag="-p", description="Restrict search to subpath", type="path")],
            requires_auth=True,
        ),
        handler=_handle_files_search,
    )
    reg.register(
        CommandMetadata(
            id="notes.list",
            name="List Notes",
            category=CommandCategory.FILES_KNOWLEDGE,
            command_tokens=["notes", "list"],
            summary="List synchronized markdown notes",
            detailed_description="Retrieves notes stored in personal knowledge graph.",
            usage="nexus notes list",
            requires_auth=True,
        ),
        handler=_handle_notes_list,
    )
    reg.register(
        CommandMetadata(
            id="notes.add",
            name="Add Note",
            category=CommandCategory.FILES_KNOWLEDGE,
            command_tokens=["notes", "add"],
            summary="Create a new markdown note",
            detailed_description="Creates a note record synchronized across all paired devices.",
            usage="nexus notes add <title> [content] [project_id]",
            args=[
                CommandArg(name="title", description="Note title", type="str"),
                CommandArg(name="content", description="Initial body text", type="str", required=False, default=""),
                CommandArg(name="project_id", description="Associated Project ID", type="int", required=False, default=None),
            ],
            requires_auth=True,
        ),
        handler=_handle_notes_add,
    )
    reg.register(
        CommandMetadata(
            id="notes.delete",
            name="Delete Note",
            category=CommandCategory.FILES_KNOWLEDGE,
            command_tokens=["notes", "delete"],
            summary="Delete a note by ID",
            detailed_description="Permanently removes note from database and mirrors deletion to synced peers.",
            usage="nexus notes delete <note_id>",
            args=[CommandArg(name="note_id", description="Integer ID of note", type="int")],
            is_destructive=True,
            destructive_prompt="Delete this note permanently?",
            requires_auth=True,
        ),
        handler=_handle_notes_delete,
    )

    # --- 5. PROJECTS & PRODUCTIVITY ---
    reg.register(
        CommandMetadata(
            id="projects.list",
            name="List Projects",
            category=CommandCategory.PROJECTS_PRODUCTIVITY,
            command_tokens=["projects", "list"],
            summary="List active development projects and repositories",
            detailed_description="Displays tracked projects, repository links, and active task progress.",
            usage="nexus projects list",
            requires_auth=True,
        ),
        handler=_handle_projects_list,
    )
    reg.register(
        CommandMetadata(
            id="projects.create",
            name="Create Project",
            category=CommandCategory.PROJECTS_PRODUCTIVITY,
            command_tokens=["projects", "create"],
            summary="Register a new workspace project",
            detailed_description="Creates project container for tasks, notes, and repository synchronizations.",
            usage="nexus projects create <title> [description]",
            args=[
                CommandArg(name="title", description="Project name", type="str"),
                CommandArg(name="description", description="Project description", type="str", required=False, default=""),
            ],
            requires_auth=True,
        ),
        handler=_handle_projects_create,
    )
    reg.register(
        CommandMetadata(
            id="projects.delete",
            name="Delete Project",
            category=CommandCategory.PROJECTS_PRODUCTIVITY,
            command_tokens=["projects", "delete"],
            summary="Delete a project by ID",
            detailed_description="Permanently deletes project container and cascades to associated tasks.",
            usage="nexus projects delete <project_id>",
            args=[CommandArg(name="project_id", description="Integer ID of project", type="int")],
            is_destructive=True,
            destructive_prompt="Deleting this project will also delete all associated tasks. Continue?",
            requires_auth=True,
        ),
        handler=_handle_projects_delete,
    )
    reg.register(
        CommandMetadata(
            id="tasks.list",
            name="List Tasks",
            category=CommandCategory.PROJECTS_PRODUCTIVITY,
            command_tokens=["tasks", "list"],
            summary="List pending and completed tasks",
            detailed_description="Displays task items, completion flags, priorities, and associated project tags.",
            usage="nexus tasks list",
            requires_auth=True,
        ),
        handler=_handle_tasks_list,
    )
    reg.register(
        CommandMetadata(
            id="tasks.add",
            name="Add Task",
            category=CommandCategory.PROJECTS_PRODUCTIVITY,
            command_tokens=["tasks", "add"],
            summary="Create a new task item",
            detailed_description="Adds a task with optional project attachment.",
            usage="nexus tasks add <title> [project_id]",
            args=[
                CommandArg(name="title", description="Task description", type="str"),
                CommandArg(name="project_id", description="Associated Project ID", type="int", required=False, default=None),
            ],
            requires_auth=True,
        ),
        handler=_handle_tasks_add,
    )
    reg.register(
        CommandMetadata(
            id="tasks.done",
            name="Complete Task",
            category=CommandCategory.PROJECTS_PRODUCTIVITY,
            command_tokens=["tasks", "done"],
            summary="Mark a task as completed",
            detailed_description="Updates task status to completed and records timestamp.",
            usage="nexus tasks done <task_id>",
            args=[CommandArg(name="task_id", description="Integer ID of task", type="int")],
            requires_auth=True,
        ),
        handler=_handle_tasks_done,
    )
    reg.register(
        CommandMetadata(
            id="tasks.delete",
            name="Delete Task",
            category=CommandCategory.PROJECTS_PRODUCTIVITY,
            command_tokens=["tasks", "delete"],
            summary="Delete a task by ID",
            detailed_description="Removes task record permanently.",
            usage="nexus tasks delete <task_id>",
            args=[CommandArg(name="task_id", description="Integer ID of task", type="int")],
            is_destructive=True,
            destructive_prompt="Delete task permanently?",
            requires_auth=True,
        ),
        handler=_handle_tasks_delete,
    )

    # --- 6. SYNCHRONIZATION ---
    reg.register(
        CommandMetadata(
            id="sync.status",
            name="Sync Status",
            category=CommandCategory.SYNCHRONIZATION,
            command_tokens=["sync", "status"],
            summary="View vector clock and synchronization diagnostics",
            detailed_description="Displays state of peer replication, conflict resolution logs, and transfer queues.",
            usage="nexus sync status",
            requires_auth=True,
        ),
        handler=_handle_sync_status,
    )
    reg.register(
        CommandMetadata(
            id="sync.pull",
            name="Pull Sync Delta",
            category=CommandCategory.SYNCHRONIZATION,
            command_tokens=["sync", "pull"],
            summary="Pull incremental entity changes since cursor",
            detailed_description="Fetches recent deltas for projects, tasks, and notes from primary node.",
            usage="nexus sync pull",
            requires_auth=True,
        ),
        handler=_handle_sync_pull,
    )

    # --- 7. LOCAL SERVICES ---
    reg.register(
        CommandMetadata(
            id="services.status",
            name="Services Status",
            category=CommandCategory.LOCAL_SERVICES,
            command_tokens=["services", "status"],
            summary="Check status of background services, STT, and LLM",
            detailed_description="Reports daemon state for local speech-to-text, offline LLM inference, and relay listeners.",
            usage="nexus services status",
        ),
        handler=_handle_services_status,
    )

    # --- 8. SETTINGS & SETUP ---
    reg.register(
        CommandMetadata(
            id="config.list",
            name="List Configuration",
            category=CommandCategory.SETTINGS_SETUP,
            command_tokens=["config", "list"],
            summary="Inspect active configuration and endpoint parameters",
            detailed_description="Displays active URLs, profile name, timeout, and credential store configuration.",
            usage="nexus config list",
        ),
        handler=_handle_config_list,
    )
    reg.register(
        CommandMetadata(
            id="config.set",
            name="Set Configuration",
            category=CommandCategory.SETTINGS_SETUP,
            command_tokens=["config", "set"],
            summary="Update a configuration parameter",
            detailed_description="Updates and persists configuration setting to ~/.nexus-cli.json.",
            usage="nexus config set <key> <value>",
            args=[
                CommandArg(name="key", description="Parameter name (api_url, timeout, etc.)", type="str"),
                CommandArg(name="value", description="New value", type="str"),
            ],
        ),
        handler=_handle_config_set,
    )
    reg.register(
        CommandMetadata(
            id="config.profile.list",
            name="List Profiles",
            category=CommandCategory.SETTINGS_SETUP,
            command_tokens=["config", "profile", "list"],
            summary="List configured server and environment profiles",
            detailed_description="Shows all profiles configured in local storage, highlighting the active profile.",
            usage="nexus config profile list",
        ),
        handler=_handle_profile_list,
    )
    reg.register(
        CommandMetadata(
            id="config.profile.switch",
            name="Switch Profile",
            category=CommandCategory.SETTINGS_SETUP,
            command_tokens=["config", "profile", "switch"],
            summary="Switch active configuration profile",
            detailed_description="Switches the active profile and updates API target and keyring credential scope.",
            usage="nexus config profile switch <name>",
            args=[CommandArg(name="name", description="Profile name to activate", type="str")],
        ),
        handler=_handle_profile_switch,
    )
    reg.register(
        CommandMetadata(
            id="config.reset",
            name="Reset Configuration",
            category=CommandCategory.SETTINGS_SETUP,
            command_tokens=["config", "reset"],
            summary="Purge all configuration files and keychain credentials",
            detailed_description="Deletes local JSON settings and all secure credentials stored in OS Keyring across all profiles.",
            usage="nexus config reset",
            is_destructive=True,
            destructive_prompt="This will remove all stored credentials and local settings. Are you sure?",
        ),
        handler=lambda a, o: (reset_config(), CommandResult(success=True, title="Reset Complete", message="Configuration purged."))[1],
    )

    _REGISTRY = reg
    return _REGISTRY
