"""Tests for nexus host command suite."""

from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from nexus_cli.cli import app

runner = CliRunner()


def test_host_status_offline():
    """Verify nexus host status reports offline when host is down."""
    with patch("requests.get", side_effect=Exception("Connection refused")):
        res = runner.invoke(app, ["host", "status"])
        assert res.exit_code == 0
        assert "HOST OFFLINE" in res.output or "OFFLINE" in res.output


def test_host_status_online_mocked():
    """Verify nexus host status parses telemetry successfully."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "online",
        "service": "nexus-host",
        "mode": "node",
        "hostname": "mac-host.local",
        "platform": "darwin",
        "port": 8000,
        "database": {"engine": "sqlite", "path": "/Users/test/.nexus/nexus.db", "size_bytes": 10240, "wal_enabled": True},
        "lan_ips": ["192.168.1.100"],
        "counts": {"projects": 3, "tasks": 5, "notes": 2, "devices": 1},
    }
    with patch("requests.get", return_value=mock_resp):
        res = runner.invoke(app, ["host", "status"])
        assert res.exit_code == 0
        assert "mac-host.local" in res.output
        assert "192.168.1.100:8000" in res.output


def test_host_pair_output():
    """Verify nexus host pair outputs valid connection string and PIN."""
    res = runner.invoke(app, ["host", "pair", "--json"])
    assert res.exit_code == 0
    import json
    data = json.loads(res.output)
    assert data["type"] == "nexus_host_pairing"
    assert "url" in data
    assert "code" in data
    assert len(data["code"]) == 6
    assert "nexus://pair" in data["pairing_uri"]
