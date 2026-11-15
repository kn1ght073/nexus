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
