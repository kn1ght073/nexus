"""Pytest configuration: fresh DB + jailed storage roots per test session.

Settings are injected through the environment (NEXUS_*), which
pydantic-settings reads natively. The app is imported once, after the
env vars are set, and tables are recreated per test for isolation.
"""
import json
import os
import sys
from pathlib import Path

import pytest

# Ensure the service package is importable when running from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def storage_root(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("storage")
    (root / "docs").mkdir()
    (root / "docs" / "report.txt").write_text(
        "The networking assignment is due Thursday", encoding="utf-8"
    )
    (root / "secret_inside.txt").write_text("this file is inside the root", encoding="utf-8")
    (root / "docs" / "big.txt").write_text("x" * 1_100_000, encoding="utf-8")  # >1MB: skipped
    # a sibling outside the jail to prove traversal rejection
    outside = root.parent / "outside"
    outside.mkdir(exist_ok=True)
    (outside / "root").write_text("root:x:0:0", encoding="utf-8")
    return root


@pytest.fixture(scope="session")
def env(storage_root, tmp_path_factory):
    """Set NEXUS_* env vars, then import the app once with those settings."""
    db_dir = tmp_path_factory.mktemp("db")
    overrides = {
        "NEXUS_DATABASE_PATH": str(db_dir / "test.db"),
        "NEXUS_DATABASE_URL": "",  # Protect ambient Postgres from being hit/dropped during tests (F20)
        "NEXUS_JWT_SECRET_FILE": str(db_dir / "jwt_secret"),
        # list[str] fields are JSON-decoded from env by pydantic-settings
        "NEXUS_STORAGE_ROOTS": json.dumps([str(storage_root)]),
        # Every test re-registers user_a/user_b from the same TestClient IP;
        # relax (but do not disable) the register/login limits for the suite.
        "NEXUS_AUTH_RATE_LIMIT": "1000",
        # Account lockout would poison later tests after the lockout test
        # runs; the limiter itself is reset between tests via the reset hook.
        "NEXUS_AUTH_LOCKOUT_SECONDS": "1",
    }
    saved = {k: os.environ.get(k) for k in overrides}
    os.environ.update(overrides)

    import nexus_core.settings as settings_mod

    settings_mod.get_settings.cache_clear()
    import nexus_core.database as database_mod

    import nexus_core.main as main_mod

    app = main_mod.app
    engine = database_mod.engine

    yield {"app": app, "engine": engine}

    database_mod.Base.metadata.drop_all(bind=engine)
    engine.dispose()
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    settings_mod.get_settings.cache_clear()


@pytest.fixture(autouse=True)
def fresh_tables(env):
    """Recreate a clean schema before every test (rows never leak across)."""
    from nexus_core.database import Base

    Base.metadata.drop_all(bind=env["engine"])
    Base.metadata.create_all(bind=env["engine"])
    # auth hardening state is in-memory; reset it so one test's lockout /
    # throttling cannot bleed into the next test's logins.
    from nexus_core.routers import auth as auth_router

    auth_router._login_limiter._events.clear()
    auth_router._register_limiter._events.clear()
    auth_router._account_lockout._failed.clear()
    auth_router._account_lockout._locked_at.clear()
    from nexus_core.routers import relay as relay_router

    relay_router._pairing_limiter._events.clear()
    relay_router._attach_limiter._events.clear()
    yield


@pytest.fixture()
def client(env):
    from fastapi.testclient import TestClient

    with TestClient(env["app"]) as c:
        yield c


import base64


def _create_google_user(client, email: str, sub: str):
    start = client.post("/api/auth/google/start", json={}).json()
    claims = {
        "sub": sub,
        "email": email,
        "email_verified": True,
        "name": email.split("@")[0],
    }
    mock_code = "mock_token_" + base64.urlsafe_b64encode(json.dumps(claims).encode()).decode()
    resp = client.post(
        "/api/auth/google/callback",
        json={
            "code": mock_code,
            "state": start["state"],
            "code_verifier": start["code_verifier"],
        },
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    return {
        "token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
    }


@pytest.fixture()
def user_a(client):
    """Registered user A provisioned via Google OAuth."""
    return _create_google_user(client, "a@nexus.example.com", "google-sub-user-a")


@pytest.fixture()
def user_b(client):
    """Registered user B provisioned via Google OAuth (isolation tests)."""
    return _create_google_user(client, "b@nexus.example.com", "google-sub-user-b")
