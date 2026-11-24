"""Tests for Control-Plane token exchange, Project full PATCH updates, and NodeBridge auth forwarding."""
import asyncio
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _make_client_and_user(tmp_path, monkeypatch):
    import nexus_core.settings as settings_mod
    import nexus_core.database as db_mod
    import nexus_core.security as sec_mod
    import nexus_core.main as main_mod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    monkeypatch.setenv("NEXUS_DATABASE_PATH", str(tmp_path / "node_cp_ex.db"))
    monkeypatch.setenv("NEXUS_CONTROL_PLANE_MODE", "false")
    monkeypatch.setenv("NEXUS_JWT_SECRET", "local-node-secret-for-testing-only-123456")
    settings_mod.get_settings.cache_clear()

    engine = create_engine(
        f"sqlite:///{tmp_path / 'node_cp_ex.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", sessionmaker(autocommit=False, autoflush=False, bind=engine))
    db_mod.Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(sec_mod, "_settings", settings_mod.get_settings())
    monkeypatch.setattr(sec_mod, "JWT_SECRET", "local-node-secret-for-testing-only-123456")
    monkeypatch.setattr(main_mod, "settings", settings_mod.get_settings())

    app = main_mod.create_app()
    return TestClient(app), engine, settings_mod


def test_cp_exchange_provisions_local_user_and_grants_node_access(tmp_path, monkeypatch):
    client, engine, settings_mod = _make_client_and_user(tmp_path, monkeypatch)
    try:
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            "id": 99,
            "email": "operator@example.com",
            "display_name": "Operator",
        }

        with patch("nexus_core.routers.auth._requests.get", return_value=fake_resp) as mock_get:
            res = client.post("/api/auth/cp-exchange", json={"token": "cp-jwt-token-value-12345"})
            assert res.status_code == 200, res.text
            tokens = res.json()
            assert tokens["access_token"]
            assert tokens["refresh_token"]
            mock_get.assert_called_once()

        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        me_res = client.get("/api/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "operator@example.com"

        # Full project CRUD including PATCH title/description
        proj = client.post("/api/projects", json={"title": "Initial", "description": "Old desc"}, headers=headers)
        assert proj.status_code == 201
        pid = proj.json()["id"]

        upd = client.patch(
            f"/api/projects/{pid}",
            json={"title": "Updated", "description": "New desc", "status": "in_progress"},
            headers=headers,
        )
        assert upd.status_code == 200
        assert upd.json()["title"] == "Updated"
        assert upd.json()["description"] == "New desc"
        assert upd.json()["status"] == "in_progress"
    finally:
        engine.dispose()
        settings_mod.get_settings.cache_clear()


def test_cp_exchange_rejects_invalid_control_plane_token(tmp_path, monkeypatch):
    client, engine, settings_mod = _make_client_and_user(tmp_path, monkeypatch)
    try:
        fake_resp = MagicMock()
        fake_resp.status_code = 401
        with patch("nexus_core.routers.auth._requests.get", return_value=fake_resp):
            res = client.post("/api/auth/cp-exchange", json={"token": "invalid-cp-token-12345"})
            assert res.status_code == 401
    finally:
        engine.dispose()
        settings_mod.get_settings.cache_clear()


def test_node_bridge_promotes_node_authorization_header():
    from nexus_core.node_bridge import NodeBridge

    captured = {}

    async def fake_app(scope, receive, send):
        captured["headers"] = {k.decode(): v.decode() for k, v in scope["headers"]}
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok":true}'})

    bridge = NodeBridge("https://example.com", 1, "key", app=fake_app)
    res = asyncio.run(
        bridge._execute(
            {
                "method": "GET",
                "path": "/api/projects",
                "headers": {
                    "Authorization": "Bearer cp-token",
                    "X-Nexus-Node-Authorization": "Bearer local-node-token",
                },
                "body_b64": "",
            }
        )
    )
    assert res["status"] == 200
    assert captured["headers"]["authorization"] == "Bearer local-node-token"
    assert "x-nexus-node-authorization" not in captured["headers"]
