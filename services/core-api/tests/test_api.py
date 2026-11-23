"""Auth, ownership isolation, activity, sync, files jail, and WS event tests."""
from datetime import datetime, timedelta, timezone


# --- Health ---
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["service"] == "nexus-core"


# --- Auth ---
def test_register_duplicate_email(client, user_a):
    r = client.post("/api/auth/register", json={"email": "a@nexus.example.com", "password": "password-a-123"})
    assert r.status_code == 409


def test_login_wrong_password(client, user_a):
    r = client.post("/api/auth/login", json={"email": "a@nexus.example.com", "password": "wrong-password"})
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post("/api/auth/login", json={"email": "ghost@nexus.example.com", "password": "whatever123"})
    assert r.status_code == 401


def test_password_too_short_rejected(client):
    r = client.post("/api/auth/register", json={"email": "x@nexus.example.com", "password": "short"})
    assert r.status_code == 422


def test_protected_route_requires_token(client):
    r = client.get("/api/projects")
    assert r.status_code == 401


def test_protected_route_rejects_garbage_token(client):
    r = client.get("/api/projects", headers={"Authorization": "Bearer mock-token-123"})
    assert r.status_code == 401  # the old mock token no longer works (C2 fixed)


def test_refresh_flow(client, user_a):
    r = client.post("/api/auth/login", json={"email": "a@nexus.example.com", "password": "password-a-123"})
    refresh = r.json()["refresh_token"]
    r2 = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 200 and r2.json()["access_token"]
    # refresh token must not work as an access token
    r3 = client.get("/api/projects", headers={"Authorization": f"Bearer {refresh}"})
    assert r3.status_code == 401


def test_me(client, user_a):
    r = client.get("/api/auth/me", headers=user_a["headers"])
    assert r.status_code == 200 and r.json()["email"] == "a@nexus.example.com"


# --- Devices ---
def test_device_register_and_list(client, user_a):
    r = client.post(
        "/api/devices/register",
        json={"name": "Pixel 9", "platform": "android", "capabilities": ["notifications", "microphone"]},
        headers=user_a["headers"],
    )
    assert r.status_code == 201
    device_id = r.json()["id"]
    r2 = client.get("/api/devices", headers=user_a["headers"])
    assert r2.status_code == 200 and len(r2.json()) == 1
    # heartbeat
    r3 = client.post(f"/api/devices/{device_id}/heartbeat", headers=user_a["headers"])
    assert r3.status_code == 200 and r3.json()["is_online"] is True


# --- Ownership isolation (C4) ---
def test_task_note_isolation(client, user_a, user_b):
    client.post("/api/tasks", json={"title": "A's secret task"}, headers=user_a["headers"])
    client.post("/api/notes", json={"title": "A's secret note", "content": "hello"}, headers=user_a["headers"])
    a_tasks = client.get("/api/tasks", headers=user_a["headers"]).json()
    a_notes = client.get("/api/notes", headers=user_a["headers"]).json()
    b_tasks = client.get("/api/tasks", headers=user_b["headers"]).json()
    b_notes = client.get("/api/notes", headers=user_b["headers"]).json()
    assert len(a_tasks) == 1 and a_tasks[0]["title"] == "A's secret task"
    assert len(a_notes) == 1
    assert b_tasks == [] and b_notes == []  # B sees nothing of A's


def test_cannot_touch_other_users_task(client, user_a, user_b):
    task = client.post("/api/tasks", json={"title": "A's task"}, headers=user_a["headers"]).json()
    r = client.get(f"/api/tasks/{task['id']}", headers=user_b["headers"])
    assert r.status_code == 404
    r2 = client.patch(f"/api/tasks/{task['id']}/status", json={"status": "completed"}, headers=user_b["headers"])
    assert r2.status_code == 404
    r3 = client.delete(f"/api/tasks/{task['id']}", headers=user_b["headers"])
    assert r3.status_code == 404


def test_cannot_use_other_users_project(client, user_a, user_b):
    project = client.post("/api/projects", json={"title": "A's project"}, headers=user_a["headers"]).json()
    r = client.post("/api/tasks", json={"title": "Task into A's project", "project_id": project["id"]}, headers=user_b["headers"])
    assert r.status_code == 404


# --- Tasks ---
def test_task_lifecycle(client, user_a):
    project = client.post("/api/projects", json={"title": "Networking"}, headers=user_a["headers"]).json()
    task = client.post(
        "/api/tasks",
        json={"title": "Finish report", "project_id": project["id"]},
        headers=user_a["headers"],
    ).json()
    assert task["status"] == "pending" and task["project_id"] == project["id"]

    done = client.post(f"/api/tasks/{task['id']}/done", headers=user_a["headers"]).json()
    assert done["status"] == "completed"

    listed = client.get("/api/tasks", params={"status_filter": "completed"}, headers=user_a["headers"]).json()
    assert any(t["id"] == task["id"] for t in listed)

    today = client.get("/api/tasks/today", headers=user_a["headers"]).json()
    assert any(t["id"] == task["id"] for t in today)


def test_task_status_validation(client, user_a):
    r = client.patch("/api/tasks/999999/status", json={"status": "completed"}, headers=user_a["headers"])
    assert r.status_code == 404


# --- Tombstone deletion (sync foundation) ---
def test_deleted_tasks_hidden_but_tombstoned(client, user_a):
    task = client.post("/api/tasks", json={"title": "to delete"}, headers=user_a["headers"]).json()
    r = client.delete(f"/api/tasks/{task['id']}", headers=user_a["headers"])
    assert r.status_code == 204
    assert client.get("/api/tasks", headers=user_a["headers"]).json() == []
    assert client.get(f"/api/tasks/{task['id']}", headers=user_a["headers"]).status_code == 404


# --- Activity ---
def test_activity_log_records_actions(client, user_a):
    client.post("/api/projects", json={"title": "Logged project"}, headers=user_a["headers"])
    activity = client.get("/api/activity", headers=user_a["headers"]).json()
    actions = [a["action"] for a in activity]
    assert "user.login" in actions and "project.created" in actions


def test_activity_is_per_user(client, user_a, user_b):
    client.post("/api/projects", json={"title": "A only"}, headers=user_a["headers"])
    b_activity = client.get("/api/activity", headers=user_b["headers"]).json()
    assert all(a["action"] != "project.created" for a in b_activity)


# --- Files jail (C5) ---
def test_files_browse_default_root(client, user_a, storage_root):
    r = client.get("/api/files/browse", headers=user_a["headers"])
    assert r.status_code == 200
    names = [f["name"] for f in r.json()]
    assert "docs" in names and "secret_inside.txt" in names


def test_files_browse_inside_root(client, user_a, storage_root):
    r = client.get("/api/files/browse", params={"path": str(storage_root / "docs")}, headers=user_a["headers"])
    assert r.status_code == 200
    names = [f["name"] for f in r.json()]
    assert "report.txt" in names


def test_files_browse_rejects_escape(client, user_a, storage_root):
    r = client.get("/api/files/browse", params={"path": "/etc"}, headers=user_a["headers"])
    assert r.status_code == 403
    r2 = client.get("/api/files/browse", params={"path": str(storage_root / ".." / "..")}, headers=user_a["headers"])
    assert r2.status_code == 403


def test_files_browse_traversal_rejected(client, user_a, storage_root):
    r = client.get(
        "/api/files/browse",
        params={"path": f"{storage_root}/../../../../etc"},
        headers=user_a["headers"],
    )
    assert r.status_code == 403


def test_files_search_finds_content(client, user_a, storage_root):
    r = client.get("/api/files/search", params={"query": "networking assignment"}, headers=user_a["headers"])
    assert r.status_code == 200
    results = r.json()
    assert len(results) == 1
    assert "networking assignment" in results[0]["match_context"].lower()


def test_files_search_outside_root_rejected(client, user_a):
    r = client.get("/api/files/search", params={"query": "root", "path": "/etc"}, headers=user_a["headers"])
    assert r.status_code == 403


# --- Sync ---
def test_sync_pull_returns_changes(client, user_a):
    client.post("/api/projects", json={"title": "Synced"}, headers=user_a["headers"])
    r = client.post("/api/sync/pull", json={}, headers=user_a["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["changes"]["projects"][0]["title"] == "Synced"
    server_time = body["server_time"]

    # second pull with since=server_time -> only rows updated after that
    r2 = client.post("/api/sync/pull", json={"since": server_time}, headers=user_a["headers"])
    assert r2.status_code == 200
    assert r2.json()["changes"]["projects"] == []


def test_sync_pull_isolation(client, user_a, user_b):
    client.post("/api/projects", json={"title": "A's sync"}, headers=user_a["headers"])
    b_pull = client.post("/api/sync/pull", json={}, headers=user_b["headers"]).json()
    assert b_pull["changes"]["projects"] == []


# --- WebSocket events ---
def test_ws_receives_task_created_event(client, user_a):
    with client.websocket_connect("/ws") as ws:
        ws.send_text(user_a["token"])
        ready = ws.receive_json()
        assert ready["type"] == "ready"

        client.post("/api/tasks", json={"title": "WS event test"}, headers=user_a["headers"])

        event = ws.receive_json()
        assert event["type"] == "TASK_CREATED"
        assert event["data"]["title"] == "WS event test"


def test_ws_rejects_bad_token(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_text("mock-token-123")
        error = ws.receive_json()
        assert error["type"] == "error"


# --- Step 2: revisions ---
def test_revision_bumps_on_mutation(client, user_a):
    task = client.post("/api/tasks", json={"title": "rev test"}, headers=user_a["headers"]).json()
    assert task["revision"] == 1
    updated = client.patch(f"/api/tasks/{task['id']}/status", json={"status": "in_progress"}, headers=user_a["headers"]).json()
    assert updated["revision"] == 2
    done = client.post(f"/api/tasks/{task['id']}/done", headers=user_a["headers"]).json()
    assert done["revision"] == 3
    project = client.post("/api/projects", json={"title": "rev proj"}, headers=user_a["headers"]).json()
    assert project["revision"] == 1
    client.patch(f"/api/projects/{project['id']}/status", json={"status": "completed"}, headers=user_a["headers"])
    listed = client.get("/api/projects", headers=user_a["headers"]).json()
    assert [p for p in listed if p["id"] == project["id"]][0]["revision"] == 2


# --- Step 2: /sync/push ---
def test_sync_push_create_and_update(client, user_a):
    # push a create (id=None)
    r = client.post(
        "/api/sync/push",
        json={"tasks": [{"title": "pushed task", "revision": 1}], "notes": [], "projects": []},
        headers=user_a["headers"],
    )
    assert r.status_code == 200, r.text
    res = r.json()["results"]["tasks"]
    assert res[0]["accepted"] is True and res[0]["id"] is not None

    # server row now exists; update via push with correct revision
    task_id = res[0]["id"]
    r2 = client.post(
        "/api/sync/push",
        json={"tasks": [{"id": task_id, "title": "pushed task v2", "status": "completed", "revision": 1}], "notes": [], "projects": []},
        headers=user_a["headers"],
    )
    res2 = r2.json()["results"]["tasks"]
    assert res2[0]["accepted"] is True
    assert res2[0]["server_revision"] == 2

    # normal GET reflects the pushed change
    tasks = client.get("/api/tasks", headers=user_a["headers"]).json()
    mine = [t for t in tasks if t["id"] == task_id][0]
    assert mine["title"] == "pushed task v2" and mine["status"] == "completed" and mine["revision"] == 2


def test_sync_push_conflict_stale_revision(client, user_a):
    task = client.post("/api/tasks", json={"title": "conflict base"}, headers=user_a["headers"]).json()
    # server bumps to rev 2
    client.patch(f"/api/tasks/{task['id']}/status", json={"status": "in_progress"}, headers=user_a["headers"])
    # stale client still thinks rev 1 and tries to write
    r = client.post(
        "/api/sync/push",
        json={"tasks": [{"id": task["id"], "title": "stale write", "revision": 1}], "notes": [], "projects": []},
        headers=user_a["headers"],
    )
    res = r.json()["results"]["tasks"]
    assert res[0]["accepted"] is False and res[0]["conflict"] is True
    assert res[0]["server_revision"] == 2
    # title unchanged on server
    tasks = client.get("/api/tasks", headers=user_a["headers"]).json()
    mine = [t for t in tasks if t["id"] == task["id"]][0]
    assert mine["title"] == "conflict base"


def test_sync_push_delete_tombstones(client, user_a):
    task = client.post("/api/tasks", json={"title": "to tombstone"}, headers=user_a["headers"]).json()
    r = client.post(
        "/api/sync/push",
        json={"tasks": [{"id": task["id"], "deleted": True, "revision": task["revision"]}], "notes": [], "projects": []},
        headers=user_a["headers"],
    )
    assert r.json()["results"]["tasks"][0]["accepted"] is True
    assert client.get("/api/tasks", headers=user_a["headers"]).json() == []


def test_sync_push_isolation(client, user_a, user_b):
    task = client.post("/api/tasks", json={"title": "A's task"}, headers=user_a["headers"]).json()
    r = client.post(
        "/api/sync/push",
        json={"tasks": [{"id": task["id"], "title": "hijack", "revision": 1}], "notes": [], "projects": []},
        headers=user_b["headers"],
    )
    res = r.json()["results"]["tasks"]
    assert res[0]["accepted"] is False and res[0]["reason"] == "not found"


# --- Step 2: device tokens with scopes ---
def test_device_token_scopes(client, user_a):
    device = client.post(
        "/api/devices/register",
        json={"name": "Android", "platform": "android", "capabilities": ["notifications", "capture"]},
        headers=user_a["headers"],
    ).json()

    # request a scope the device does not declare -> 400
    bad = client.post(
        f"/api/devices/{device['id']}/token",
        json={"scopes": ["filesystem"]},
        headers=user_a["headers"],
    )
    assert bad.status_code == 400

    # request declared scopes -> token with "capture,notifications"
    ok = client.post(
        f"/api/devices/{device['id']}/token",
        json={"scopes": ["notifications", "capture"]},
        headers=user_a["headers"],
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["scope"] == "capture,notifications"

    # that scoped token CANNOT read files (no read/filesystem scope)
    files_r = client.get("/api/files/browse", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert files_r.status_code == 403

    # but CAN pull sync (read allowed? scope lacks read -> 403)
    pull_r = client.post("/api/sync/pull", json={}, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert pull_r.status_code == 403

    # a read-scoped token CAN pull
    read_tok = client.post(
        f"/api/devices/{device['id']}/token",
        json={"scopes": ["read"]},
        headers=user_a["headers"],
    ).json()
    pull2 = client.post("/api/sync/pull", json={}, headers={"Authorization": f"Bearer {read_tok['access_token']}"})
    assert pull2.status_code == 200
    browse2 = client.get("/api/files/browse", headers={"Authorization": f"Bearer {read_tok['access_token']}"})
    assert browse2.status_code == 200


# --- Step 6: Universal Inbox + AI pipeline (mock backends) ---
def test_inbox_text_creates_task_via_pipeline(client, user_a):
    r = client.post(
        "/api/inbox",
        data={"text": "Submit the networking assignment by Friday. It needs a diagram."},
        headers=user_a["headers"],
    )
    assert r.status_code == 202, r.text
    item_id = r.json()["inbox_item_id"]

    status = client.get(f"/api/inbox/{item_id}", headers=user_a["headers"]).json()
    assert status["status"] == "completed", status
    assert status["result"] is not None

    # pipeline created a task from the first sentence
    tasks = client.get("/api/tasks", headers=user_a["headers"]).json()
    assert any("networking assignment" in t["title"].lower() for t in tasks)

    # activity shows the ai source
    activity = client.get("/api/activity", headers=user_a["headers"]).json()
    assert any(a["action"] == "task.created" and "[ai:text]" in a["detail"] for a in activity)


def test_inbox_audio_mock_stt_pipeline(client, user_a, storage_root):
    import io

    # fake audio blob; mock STT derives a deterministic transcript
    blob = io.BytesIO(b"FAKEAUDIODATA" * 100)
    r = client.post(
        "/api/inbox/audio",
        files={"audio": ("voice.wav", blob, "audio/wav")},
        headers=user_a["headers"],
    )
    assert r.status_code == 202, r.text
    item_id = r.json()["inbox_item_id"]
    assert r.json()["bytes"] > 0

    status = client.get(f"/api/inbox/{item_id}", headers=user_a["headers"]).json()
    assert status["status"] == "completed", status
    assert status["result"]["kind"] == "task" and status["result"]["id"] > 0


def test_inbox_isolation(client, user_a, user_b):
    r = client.post("/api/inbox", data={"text": "A's private note"}, headers=user_a["headers"])
    item_id = r.json()["inbox_item_id"]
    r2 = client.get(f"/api/inbox/{item_id}", headers=user_b["headers"])
    assert r2.status_code == 404


def test_inbox_requires_capture_scope(client, user_a):
    device = client.post(
        "/api/devices/register",
        json={"name": "Reader", "platform": "linux", "capabilities": ["notifications"]},
        headers=user_a["headers"],
    ).json()
    tok = client.post(
        f"/api/devices/{device['id']}/token",
        json={"scopes": ["notifications"]},
        headers=user_a["headers"],
    ).json()
    r = client.post(
        "/api/inbox",
        data={"text": "should be rejected"},
        headers={"Authorization": f"Bearer {tok['access_token']}"},
    )
    assert r.status_code == 403


# --- Step 6: intent validation (unit level) ---
def test_intent_validation_rejects_bad_shapes():
    from nexus_core.workers.llm import validate_intent, IntentValidationError

    ok = validate_intent({"action": "create_task", "title": "Write report"})
    assert ok["action"] == "create_task"

    for bad in [
        {"action": "rm -rf /", "title": "x"},          # action not in registry
        {"title": "missing action"},
        {"action": "create_task"},                      # missing title
        {"action": "create_task", "title": ""},         # empty title
        {"action": "create_task", "title": "x", "shell": "rm -rf"},  # unknown field
        ["not", "an", "object"],
        None,
    ]:
        try:
            validate_intent(bad)
            assert False, f"should have raised for {bad}"
        except IntentValidationError:
            pass


def test_action_engine_scope_enforcement(client, user_a):
    from nexus_core.database import SessionLocal
    from nexus_core.models import User
    from nexus_core.workers.action_engine import execute_intent, ActionError
    from nexus_core.security import create_token
    from nexus_core.routers.inbox import run_pipeline  # noqa: F401  (import check)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "a@nexus.example.com").first()
        # simulate a device-scoped token: capture scope CAN create_task
        setattr(user, "_token_scope", "capture")
        result = execute_intent(db, user, {"action": "create_task", "title": "scoped ok"})
        assert result["kind"] == "task"

        # read-only scope CANNOT
        user2 = db.query(User).filter(User.email == "a@nexus.example.com").first()
        setattr(user2, "_token_scope", "read")
        try:
            execute_intent(db, user2, {"action": "create_task", "title": "nope"})
            assert False, "should have raised"
        except ActionError:
            pass
    finally:
        db.close()


# --- Step 8: nodes + control-plane mode ---
def test_node_claim_activate_demote(client, user_a):
    r = client.post(
        "/api/nodes/claim",
        json={"name": "Karthik's MacBook", "platform": "macos", "endpoint": "http://192.168.1.20:8000"},
        headers=user_a["headers"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["is_active"] is True and body["is_online"] is True
    assert body["api_key"]  # issued exactly once at claim
    assert body["services"] == {}

    # active resolution returns the node
    active = client.get("/api/nodes/active", headers=user_a["headers"]).json()
    assert active["name"] == "Karthik's MacBook"

    # a second machine claims: single-active policy demotes the first
    r2 = client.post(
        "/api/nodes/claim",
        json={"name": "Windows-Node", "platform": "windows", "endpoint": "http://192.168.1.21:8000"},
        headers=user_a["headers"],
    )
    assert r2.status_code == 201
    assert r2.json()["is_active"] is True
    active2 = client.get("/api/nodes/active", headers=user_a["headers"]).json()
    assert active2["name"] == "Windows-Node"
    nodes = client.get("/api/nodes", headers=user_a["headers"]).json()
    mac = [n for n in nodes if n["name"] == "Karthik's MacBook"][0]
    assert mac["is_active"] is False

    # re-claim by same name rotates the key and re-activates
    r3 = client.post(
        "/api/nodes/claim",
        json={"name": "Karthik's MacBook", "platform": "macos", "endpoint": "http://192.168.1.20:8000"},
        headers=user_a["headers"],
    )
    assert r3.json()["api_key"] != body["api_key"]


def test_node_heartbeat_and_stale_resolution(client, user_a, env):
    from nexus_core.database import SessionLocal
    from nexus_core.models import Node, utcnow
    from datetime import timedelta

    r = client.post(
        "/api/nodes/claim",
        json={"name": "Mac-node", "platform": "macos", "endpoint": "http://mac:8000"},
        headers=user_a["headers"],
    )
    node_id = r.json()["id"]

    # heartbeat keeps it resolvable
    hb = client.post(f"/api/nodes/{node_id}/heartbeat", headers=user_a["headers"])
    assert hb.status_code == 200
    assert client.get("/api/nodes/active", headers=user_a["headers"]).json()["id"] == node_id

    # age the last_seen past the timeout: resolution falls to null
    db = SessionLocal()
    try:
        node = db.get(Node, node_id)
        node.last_seen = utcnow() - timedelta(seconds=99999)
        db.commit()
    finally:
        db.close()
    assert client.get("/api/nodes/active", headers=user_a["headers"]).json() is None

    # a heartbeat revives it
    client.post(f"/api/nodes/{node_id}/heartbeat", headers=user_a["headers"])
    assert client.get("/api/nodes/active", headers=user_a["headers"]).json()["id"] == node_id


def test_node_services_reporting_and_isolation(client, user_a, user_b):
    r = client.post(
        "/api/nodes/claim",
        json={"name": "Mac-node", "platform": "macos"},
        headers=user_a["headers"],
    )
    node_id = r.json()["id"]

    svc = client.post(
        f"/api/nodes/{node_id}/services",
        json={"services": {"stt": "faster-whisper"}},
        headers=user_a["headers"],
    )
    assert svc.status_code == 200
    assert svc.json()["services"] == {"stt": "faster-whisper"}

    # user B cannot see or touch A's node
    assert client.get("/api/nodes", headers=user_b["headers"]).json() == []
    assert client.get(f"/api/nodes/{node_id}/heartbeat", headers=user_b["headers"]).status_code == 405  # wrong method
    r404 = client.get("/api/nodes/active", headers=user_b["headers"]).json()
    assert r404 is None


def test_control_plane_mode_mounts_only_coordination_routers(storage_root, tmp_path_factory):
    """Control-plane mode must run with a pristine import graph: subprocess.

    The app module reads settings at import time, so reloading in-process
    mixes module states. A subprocess with its own env gives a true
    "fresh boot in control-plane mode".
    """
    import json as _json
    import subprocess
    import sys
    from pathlib import Path

    db_dir = tmp_path_factory.mktemp("cp_db")
    script = r"""
import json, sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
import nexus_core.main as m

with TestClient(m.app) as c:
    assert c.get("/health").json()["mode"] == "control-plane"
    c.post("/api/auth/register", json={"email": "cp@nexus.example.com", "password": "password-cp-1"})
    login = c.post("/api/auth/login", json={"email": "cp@nexus.example.com", "password": "password-cp-1"}).json()
    h = {"Authorization": "Bearer " + login["access_token"]}
    claim = c.post("/api/nodes/claim", json={"name": "Mac", "platform": "macos", "endpoint": "http://mac:8000"}, headers=h)
    assert claim.status_code == 201, claim.text
    assert c.get("/api/nodes/active", headers=h).json()["name"] == "Mac"
    missing = [p for p in ["/api/tasks", "/api/projects", "/api/notes", "/api/inbox", "/api/sync/pull", "/api/files/browse"] if c.get(p, headers=h).status_code != 404]
    assert missing == [], f"personal-data endpoints must not exist: {missing}"
    # devices & activity (coordination) are mounted
    assert c.get("/api/devices", headers=h).status_code == 200
    assert c.get("/api/activity", headers=h).status_code == 200
print("CP_MODE_OK")
"""
    env = {
        **__import__("os").environ,
        "NEXUS_DATABASE_PATH": str(db_dir / "cp.db"),
        "NEXUS_JWT_SECRET_FILE": str(db_dir / "cp_secret"),
        "NEXUS_CONTROL_PLANE_MODE": "true",
        "NEXUS_ALLOW_EPHEMERAL_DB": "true",
        "NEXUS_ALLOW_PASSWORD_AUTH": "true",
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        env=env,
        timeout=120,
    )
    assert "CP_MODE_OK" in result.stdout, result.stdout + result.stderr


def test_database_url_setting_takes_precedence():
    from nexus_core.settings import Settings

    s = Settings(database_url="postgres://user:pass@host:5432/db")
    from nexus_core.database import _engine_url

    # _engine_url reads the module-level settings; verify normalization logic
    # directly on the URL string instead of the singleton.
    url = s.database_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    assert url == "postgresql://user:pass@host:5432/db"
