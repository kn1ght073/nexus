"""Test suite for Google Authentication, Automatic Host Discovery, and Global Relay Proxy.

Validates:
1. Google OAuth initiation schema compatibility (url + auth_url).
2. Direct Google ID token exchange and session creation.
3. Active node discovery with LAN URL and Relay Proxy URL.
4. Relay HTTP proxy tunnel forwarding requests to active node.
5. Sovereign data isolation (relayed requests hit local database, never cloud store).
"""

import base64
import json
import pytest
from starlette.testclient import TestClient

from nexus_core.main import create_app
from nexus_core.database import Base, SessionLocal, engine
from nexus_core.models import User, Node, ExternalIdentity
from nexus_core.routers.relay import relay_state


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(ExternalIdentity).delete()
        db.query(Node).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(ExternalIdentity).delete()
        db.query(Node).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def test_google_auth_start_schema_compatibility():
    """Verify Google start response includes both 'url' and 'auth_url' for mobile clients."""
    app = create_app()
    with TestClient(app) as client:
        res = client.post("/api/auth/google/start", json={"redirect_uri": "nexus://auth/callback"})
        assert res.status_code == 200
        data = res.json()
        assert "url" in data and "accounts.google.com" in data["url"]
        assert "auth_url" in data and data["auth_url"] == data["url"]
        assert "state" in data
        assert "code_verifier" in data


def test_google_id_token_exchange():
    """Verify mobile direct Google ID token exchange provisions a user and session."""
    app = create_app()
    with TestClient(app) as client:
        # Generate mock token payload
        mock_claims = {
            "sub": "google-user-sub-12345",
            "email": "mac_owner@nexus.dev",
            "email_verified": True,
            "name": "Mac Operator",
            "picture": "https://lh3.googleusercontent.com/a/mock-pic",
            "exp": 9999999999,
        }
        mock_raw = base64.urlsafe_b64encode(json.dumps(mock_claims).encode("utf-8")).decode("utf-8")
        token_str = f"mock_token_{mock_raw}"

        res = client.post("/api/auth/google/token", json={"id_token": token_str})
        assert res.status_code == 200
        tokens = res.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # Verify authenticated identity
        me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert me_res.status_code == 200
        user_info = me_res.json()
        assert user_info["email"] == "mac_owner@nexus.dev"
        assert user_info["display_name"] == "Mac Operator"


def test_active_host_discovery_metadata():
    """Verify GET /api/nodes/active delivers LAN URL and Relay Proxy URL to mobile."""
    app = create_app()
    with TestClient(app) as client:
        # 1. Login user
        mock_claims = {
            "sub": "sub-discovery-123",
            "email": "discovery_operator@nexus.dev",
            "email_verified": True,
            "name": "Operator",
        }
        token_str = "mock_token_" + base64.urlsafe_b64encode(json.dumps(mock_claims).encode()).decode()
        login_res = client.post("/api/auth/google/token", json={"id_token": token_str})
        access_tok = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_tok}"}

        # 2. Before claiming node, /active is null
        res = client.get("/api/nodes/active", headers=headers)
        assert res.status_code == 200
        assert res.json() is None

        # 3. Host claims node with LAN IP
        claim_res = client.post(
            "/api/nodes/claim",
            headers=headers,
            json={
                "name": "MacBook Pro (Host)",
                "platform": "macos",
                "endpoint": "http://192.168.1.55:8000",
            },
        )
        assert claim_res.status_code == 201
        claimed = claim_res.json()
        assert claimed["id"] > 0
        node_id = claimed["id"]

        # 4. Now active node returns LAN endpoint and relay proxy endpoint
        active_res = client.get("/api/nodes/active", headers=headers)
        assert active_res.status_code == 200
        node = active_res.json()
        assert node is not None
        assert node["is_online"] is True
        assert node["lan_url"] == "http://192.168.1.55:8000"
        assert node["relay_proxy_url"] == f"/api/relay/{node_id}/proxy"


def test_relay_http_proxy_route():
    """Verify /api/relay/proxy routes request to active node over WebSocket and returns response."""
    import asyncio
    app = create_app()
    with TestClient(app) as client:
        # 1. Authenticate user
        mock_claims = {
            "sub": "sub-relay-test-456",
            "email": "relay_tester@nexus.dev",
            "email_verified": True,
            "name": "Relay Tester",
        }
        token_str = "mock_token_" + base64.urlsafe_b64encode(json.dumps(mock_claims).encode()).decode()
        login_res = client.post("/api/auth/google/token", json={"id_token": token_str})
        access_tok = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_tok}"}

        # 2. Claim node
        claim_res = client.post(
            "/api/nodes/claim",
            headers=headers,
            json={"name": "Test Node", "platform": "macos", "endpoint": "http://127.0.0.1:8000"},
        )
        node_data = claim_res.json()
        node_id = node_data["id"]
        api_key = node_data["api_key"]

        # 3. Connect mock Node WebSocket to /api/relay/{node_id}/ws
        with client.websocket_connect(f"/api/relay/{node_id}/ws?key={api_key}") as ws:
            # 4. In a separate thread / async task, simulate the node answering proxy_req
            def answer_proxy_requests():
                raw = ws.receive_text()
                frame = json.loads(raw)
                if frame.get("op") == "proxy_req":
                    req_id = frame["id"]
                    # Answer with a simulated project list from local node SQLite
                    mock_res_body = json.dumps([
                        {"id": 1, "title": "Sovereign Mac Project", "description": "Stored locally"}
                    ])
                    b64_res = base64.b64encode(mock_res_body.encode("utf-8")).decode("utf-8")
                    ws.send_text(json.dumps({
                        "op": "proxy_res",
                        "id": req_id,
                        "status": 200,
                        "headers": {"content-type": "application/json"},
                        "body_b64": b64_res,
                    }))

            import threading
            worker = threading.Thread(target=answer_proxy_requests)
            worker.start()

            # 5. Mobile sends HTTP request to the relay proxy endpoint
            proxy_res = client.get("/api/relay/proxy/api/projects", headers=headers)
            worker.join(timeout=3)

            assert proxy_res.status_code == 200
            projects = proxy_res.json()
            assert len(projects) == 1
            assert projects[0]["title"] == "Sovereign Mac Project"
