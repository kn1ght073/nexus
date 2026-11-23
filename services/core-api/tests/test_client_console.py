"""Tests for the NEXUS User Client Console endpoints (/api/account/*).

Verifies:
- Account overview (Google identity, devices, sessions, role)
- Linked devices and session enumeration
- Strict account isolation (anti-IDOR / BOLA)
- Session and device revocation
- Paginated activity timeline with category filtering
- User-safe server status (zero secret leakage)
- Account data summary and sovereign storage policies
- 401 unauthorized rejection
"""
import pytest
from fastapi.testclient import TestClient


def test_unauthenticated_access_rejected(client: TestClient):
    """All /api/account endpoints must reject unauthenticated requests with 401."""
    assert client.get("/api/account/overview").status_code == 401
    assert client.get("/api/account/devices").status_code == 401
    assert client.delete("/api/account/devices/1").status_code == 401
    assert client.get("/api/account/sessions").status_code == 401
    assert client.delete("/api/account/sessions/1").status_code == 401
    assert client.get("/api/account/activity").status_code == 401
    assert client.get("/api/account/server-status").status_code == 401
    assert client.get("/api/account/data-summary").status_code == 401


def test_account_overview_happy_path(client: TestClient, user_a: dict):
    """Account overview returns correct profile, counts, and google identity."""
    res = client.get("/api/account/overview", headers=user_a["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "a@nexus.example.com"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "created_at" in data
    assert "google_identity" in data
    assert data["google_identity"]["linked"] is True
    assert data["device_stats"]["total"] == 0
    assert data["session_stats"]["total"] >= 1  # login session exists


def test_device_listing_and_revocation_isolated(client: TestClient, user_a: dict, user_b: dict):
    """Devices are strictly isolated and cross-account revocation is rejected with 404."""
    # Register device for User A
    dev_res = client.post(
        "/api/devices/register",
        json={"name": "Workstation-A", "platform": "windows", "capabilities": ["sync"]},
        headers=user_a["headers"],
    )
    assert dev_res.status_code == 201
    dev_a_id = dev_res.json()["id"]

    # User A sees the device
    list_a = client.get("/api/account/devices", headers=user_a["headers"]).json()
    assert any(d["id"] == dev_a_id and d["name"] == "Workstation-A" for d in list_a)

    # User B does NOT see User A's device
    list_b = client.get("/api/account/devices", headers=user_b["headers"]).json()
    assert not any(d["id"] == dev_a_id for d in list_b)

    # User B attempts to revoke User A's device -> 404 IDOR prevention
    del_b = client.delete(f"/api/account/devices/{dev_a_id}", headers=user_b["headers"])
    assert del_b.status_code == 404

    # User A successfully revokes own device
    del_a = client.delete(f"/api/account/devices/{dev_a_id}", headers=user_a["headers"])
    assert del_a.status_code == 204

    # Device is gone
    list_after = client.get("/api/account/devices", headers=user_a["headers"]).json()
    assert not any(d["id"] == dev_a_id for d in list_after)


def test_session_listing_and_revocation_isolated(client: TestClient, user_a: dict, user_b: dict):
    """Sessions are strictly isolated and cross-account revocation is rejected."""
    # List User A sessions
    sess_a = client.get("/api/account/sessions", headers=user_a["headers"]).json()
    assert len(sess_a) >= 1
    session_a_id = sess_a[0]["id"]

    # User B cannot see User A's session
    sess_b = client.get("/api/account/sessions", headers=user_b["headers"]).json()
    assert not any(s["id"] == session_a_id for s in sess_b)

    # User B cannot revoke User A's session -> 404
    del_b = client.delete(f"/api/account/sessions/{session_a_id}", headers=user_b["headers"])
    assert del_b.status_code == 404

    # User A revokes own session
    del_a = client.delete(f"/api/account/sessions/{session_a_id}", headers=user_a["headers"])
    assert del_a.status_code == 200
    assert del_a.json()["ok"] is True


def test_activity_pagination_and_categorization(client: TestClient, user_a: dict, user_b: dict):
    """Activity timeline supports pagination, filtering, and user isolation."""
    # Register a device to trigger activity
    client.post(
        "/api/devices/register",
        json={"name": "Phone-A", "platform": "android", "capabilities": []},
        headers=user_a["headers"],
    )

    # Fetch User A activity
    act_a = client.get("/api/account/activity?limit=10&offset=0", headers=user_a["headers"]).json()
    assert act_a["total"] >= 1
    assert len(act_a["items"]) >= 1

    # Filter by category=device
    act_device = client.get("/api/account/activity?category=device", headers=user_a["headers"]).json()
    for item in act_device["items"]:
        assert item["action"].startswith("device.")

    # Filter by category=auth
    act_auth = client.get("/api/account/activity?category=auth", headers=user_a["headers"]).json()
    for item in act_auth["items"]:
        assert item["action"].startswith("user.") or item["action"].startswith("auth.")

    # User B activity is isolated
    act_b = client.get("/api/account/activity", headers=user_b["headers"]).json()
    for item in act_b["items"]:
        assert "Phone-A" not in item["detail"]


def test_server_status_safe_and_redacted(client: TestClient, user_a: dict):
    """Server status provides health overview with zero secret leakage."""
    res = client.get("/api/account/server-status", headers=user_a["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["control_plane"] == "operational"
    assert data["database"] == "healthy"
    assert "checked_at" in data

    # Verify absence of sensitive internals
    raw_text = res.text.lower()
    for forbidden in ["postgresql://", "sqlite://", "secret", "jwt", "password", "private_key", "environ"]:
        assert forbidden not in raw_text, f"Potential sensitive leak: {forbidden}"


def test_data_summary_sovereign_policy(client: TestClient, user_a: dict):
    """Data summary reports profile, counts, and zero cloud retention storage policy."""
    res = client.get("/api/account/data-summary", headers=user_a["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["profile"]["email"] == "a@nexus.example.com"
    assert data["storage"]["cloud_bytes_stored"] == 0
    assert "Zero Cloud Retention" in data["storage"]["cloud_storage_policy"]
    assert "stats" in data


def test_client_console_html_served(client: TestClient):
    """The /client route serves the standalone Client Console interface."""
    res = client.get("/client")
    assert res.status_code == 200
    assert "NEXUS | Sovereign Client Console" in res.text
    assert "/assets/client.js" in res.text
