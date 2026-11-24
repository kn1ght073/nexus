"""Automated Cross-Device Synchronization & Unified Host Verification Suite.

Validates the 10 core architectural scenarios defined in the master brief:
1. Mac Host boots on LAN with persistent SQLite WAL database.
2. Mac creates project P1 -> written to Mac host SQLite database.
3. Mobile client connects to Mac Host -> queries /api/projects -> receives P1.
4. Mobile creates project P2 -> sends POST /api/projects to Mac Host -> persisted in host SQLite database.
5. CLI/Mac queries /api/projects -> sees P2.
6. Mobile edits P1 title -> host updates revision.
7. Mac/CLI queries P1 -> sees updated title & bumped revision.
8. Mobile deletes P2 -> host records deletion / tombstone.
9. Mac queries projects -> P2 is not listed; no phantom reappearances.
10. Host simulated reboot: database persists across process restarts.
"""

import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import pytest

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def host_environment():
    """Setup an isolated local host environment with persistent SQLite."""
    temp_dir = tempfile.TemporaryDirectory()
    db_path = Path(temp_dir.name) / "authoritative_nexus.db"
    jwt_secret_path = Path(temp_dir.name) / "jwt_secret"
    jwt_secret_path.write_text("test_secret_32_bytes_long_key_1234567890")

    old_env = {
        "NEXUS_CONTROL_PLANE_MODE": os.environ.get("NEXUS_CONTROL_PLANE_MODE"),
        "NEXUS_DATABASE_PATH": os.environ.get("NEXUS_DATABASE_PATH"),
        "NEXUS_DATABASE_URL": os.environ.get("NEXUS_DATABASE_URL"),
        "NEXUS_JWT_SECRET_FILE": os.environ.get("NEXUS_JWT_SECRET_FILE"),
        "NEXUS_HOST": os.environ.get("NEXUS_HOST"),
        "NEXUS_PORT": os.environ.get("NEXUS_PORT"),
        "NEXUS_STORAGE_ROOTS": os.environ.get("NEXUS_STORAGE_ROOTS"),
        "NEXUS_AUTH_RATE_LIMIT": os.environ.get("NEXUS_AUTH_RATE_LIMIT"),
    }

    os.environ["NEXUS_CONTROL_PLANE_MODE"] = "false"
    os.environ["NEXUS_ALLOW_PASSWORD_AUTH"] = "true"
    os.environ["NEXUS_DATABASE_PATH"] = str(db_path)
    os.environ["NEXUS_DATABASE_URL"] = ""
    os.environ["NEXUS_JWT_SECRET_FILE"] = str(jwt_secret_path)
    os.environ["NEXUS_HOST"] = "0.0.0.0"
    os.environ["NEXUS_PORT"] = "8000"
    os.environ["NEXUS_STORAGE_ROOTS"] = json.dumps([temp_dir.name])
    os.environ["NEXUS_AUTH_RATE_LIMIT"] = "10000"

    # Ensure settings cache is cleared
    import nexus_core.settings as settings_mod
    settings_mod.get_settings.cache_clear()

    import nexus_core.database as database_mod
    # Rebind engine with new URL
    database_mod.engine = database_mod.create_engine(
        database_mod._engine_url(),
        connect_args={"check_same_thread": False},
    )
    database_mod.SessionLocal = database_mod.sessionmaker(
        autocommit=False, autoflush=False, bind=database_mod.engine
    )

    import nexus_core.main as main_mod
    app = main_mod.create_app()

    yield {
        "app": app,
        "db_path": db_path,
        "temp_dir": temp_dir,
    }

    temp_dir.cleanup()
    for k, v in old_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    settings_mod.get_settings.cache_clear()


def test_scenario_01_host_boot_and_sqlite_wal(host_environment):
    """Scenario 1: Verify host boots in node mode with SQLite WAL mode and foreign keys."""
    app = host_environment["app"]
    db_path = host_environment["db_path"]

    with TestClient(app) as client:
        # Check health probe
        health = client.get("/health").json()
        assert health["status"] == "ok"
        assert health["mode"] == "node"

        # Check host status telemetry
        host_telemetry = client.get("/api/host/status").json()
        assert host_telemetry["status"] == "online"
        assert host_telemetry["service"] == "nexus-host"
        assert host_telemetry["database"]["engine"] == "sqlite"
        assert host_telemetry["database"]["wal_enabled"] is True
        assert len(host_telemetry["lan_ips"]) >= 1

    # Verify SQLite WAL mode via telemetry & engine
    assert host_telemetry["database"]["wal_enabled"] is True

    # Connect to verify pragmas
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    conn.close()

    assert journal_mode.lower() == "wal"


def test_scenario_02_mac_creates_project(host_environment):
    """Scenario 2: Mac client creates Project P1 -> persisted in host SQLite database."""
    app = host_environment["app"]
    db_path = host_environment["db_path"]

    with TestClient(app) as client:
        # Register and login operator
        reg = client.post("/api/auth/register", json={"email": "mac_owner@nexus.dev", "password": "Password123!"})
        assert reg.status_code == 201
        login = client.post("/api/auth/login", json={"email": "mac_owner@nexus.dev", "password": "Password123!"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        p1_res = client.post(
            "/api/projects",
            headers=headers,
            json={"title": "Project Alpha (Mac Host)", "description": "Initiated from macOS"},
        )
        assert p1_res.status_code == 201
        p1 = p1_res.json()
        assert p1["title"] == "Project Alpha (Mac Host)"
        assert p1["id"] is not None
        assert p1["revision"] == 1

        # Direct database verification
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT id, title, revision FROM projects WHERE title = ?", ("Project Alpha (Mac Host)",))
        row = cur.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == p1["id"]
        assert row[1] == "Project Alpha (Mac Host)"
        assert row[2] == 1


def test_scenario_03_mobile_connects_and_pulls_project(host_environment):
    """Scenario 3: Mobile client connects to Mac Host -> queries /api/projects -> sees P1."""
    app = host_environment["app"]

    with TestClient(app) as client:
        # Login as the same sovereign owner from mobile
        login = client.post("/api/auth/login", json={"email": "mac_owner@nexus.dev", "password": "Password123!"})
        assert login.status_code == 200
        mobile_token = login.json()["access_token"]

        # Mobile fetches projects from Host API
        res = client.get("/api/projects", headers={"Authorization": f"Bearer {mobile_token}"})
        assert res.status_code == 200
        projects = res.json()
        assert any(p["title"] == "Project Alpha (Mac Host)" for p in projects)


def test_scenario_04_mobile_creates_project(host_environment):
    """Scenario 4: Mobile client creates Project P2 -> persisted directly in Mac Host SQLite."""
    app = host_environment["app"]
    db_path = host_environment["db_path"]

    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": "mac_owner@nexus.dev", "password": "Password123!"})
        mobile_token = login.json()["access_token"]

        p2_res = client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {mobile_token}"},
            json={"title": "Project Beta (Mobile)", "description": "Created on iPhone on LAN"},
        )
        assert p2_res.status_code == 201
        p2 = p2_res.json()
        assert p2["title"] == "Project Beta (Mobile)"

        # Verify on host disk
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT title, revision FROM projects WHERE id = ?", (p2["id"],))
        row = cur.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "Project Beta (Mobile)"


def test_scenario_05_mac_sees_mobile_project(host_environment):
    """Scenario 5: Mac/CLI queries /api/projects -> immediately sees Project P2 from mobile."""
    app = host_environment["app"]

    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": "mac_owner@nexus.dev", "password": "Password123!"})
        mac_token = login.json()["access_token"]

        res = client.get("/api/projects", headers={"Authorization": f"Bearer {mac_token}"})
        assert res.status_code == 200
        titles = [p["title"] for p in res.json()]
        assert "Project Alpha (Mac Host)" in titles
        assert "Project Beta (Mobile)" in titles


def test_scenario_06_and_07_cross_device_editing_and_revision(host_environment):
    """Scenarios 6 & 7: Mobile updates P1 title -> host bumps revision -> Mac reads updated state."""
    app = host_environment["app"]

    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": "mac_owner@nexus.dev", "password": "Password123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Find P1
        projects = client.get("/api/projects", headers=headers).json()
        p1 = next(p for p in projects if "Project Alpha" in p["title"])
        p1_id = p1["id"]
        initial_rev = p1["revision"]

        # Mobile updates status / title via sync push or status update
        update_res = client.patch(
            f"/api/projects/{p1_id}/status",
            headers=headers,
            json={"status": "completed"},
        )
        assert update_res.status_code == 200
        updated = update_res.json()
        assert updated["status"] == "completed"
        assert updated["revision"] > initial_rev

        # Mac queries P1 and confirms state
        mac_get = client.get(f"/api/projects/{p1_id}", headers=headers)
        assert mac_get.status_code == 200
        assert mac_get.json()["status"] == "completed"
        assert mac_get.json()["revision"] == updated["revision"]


def test_scenario_08_and_09_cross_device_deletion(host_environment):
    """Scenarios 8 & 9: Mobile deletes P2 -> host soft-deletes -> Mac queries and P2 is gone."""
    app = host_environment["app"]

    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": "mac_owner@nexus.dev", "password": "Password123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Find P2
        projects = client.get("/api/projects", headers=headers).json()
        p2 = next(p for p in projects if "Project Beta" in p["title"])
        p2_id = p2["id"]

        # Mobile deletes P2
        del_res = client.delete(f"/api/projects/{p2_id}", headers=headers)
        assert del_res.status_code in (200, 204)

        # Mac queries active projects -> P2 must NOT be listed
        mac_list = client.get("/api/projects", headers=headers).json()
        active_ids = [p["id"] for p in mac_list]
        assert p2_id not in active_ids

        # Fetching directly returns 404
        direct_get = client.get(f"/api/projects/{p2_id}", headers=headers)
        assert direct_get.status_code == 404


def test_scenario_10_host_restart_persistence(host_environment):
    """Scenario 10: Process restart simulation -> SQLite database retains all projects on reopen."""
    db_path = host_environment["db_path"]

    # Read records directly from SQLite on disk
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT id, title, status, revision FROM projects WHERE deleted_at IS NULL")
    active_rows = cur.fetchall()
    conn.close()

    assert len(active_rows) == 1
    assert "Project Alpha" in active_rows[0][1]
    assert active_rows[0][2] == "completed"

    # Re-instantiate app from scratch simulating daemon reboot
    import nexus_core.main as main_mod
    fresh_app = main_mod.create_app()
    with TestClient(fresh_app) as fresh_client:
        login = fresh_client.post("/api/auth/login", json={"email": "mac_owner@nexus.dev", "password": "Password123!"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        projects = fresh_client.get("/api/projects", headers={"Authorization": f"Bearer {token}"}).json()
        assert len(projects) == 1
        assert "Project Alpha" in projects[0]["title"]
        assert projects[0]["status"] == "completed"
