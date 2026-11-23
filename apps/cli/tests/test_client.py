"""Unit tests for typed API client."""

import pytest
import requests
from unittest.mock import MagicMock, patch

from nexus_cli.client import NexusClient, get_client
from nexus_cli.config import CLIConfig
from nexus_cli.errors import (
    AuthenticationError,
    ForbiddenError,
    NetworkError,
    NotFoundError,
    TimeoutError,
)


@pytest.fixture
def test_config():
    cfg = CLIConfig(api_url="http://mock-api.local")
    cfg.token = "test-token"
    cfg.node_api_key = "test-key"
    return cfg


def test_client_headers_injection(test_config):
    client = NexusClient(config=test_config)
    headers = client._headers()
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["X-Node-API-Key"] == "test-key"
    assert "nexus-cli" in headers["User-Agent"]


def test_client_url_formatting():
    client = NexusClient(base_url="http://custom-node.local:8000/")
    assert client.base_url == "http://custom-node.local:8000"


@patch("requests.Session.request")
def test_client_error_mapping_401(mock_req, test_config):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"detail": "Invalid credentials"}
    mock_req.return_value = mock_resp

    client = NexusClient(config=test_config)
    with pytest.raises(AuthenticationError) as exc_info:
        client.get("/api/protected")
    assert "Invalid credentials" in str(exc_info.value)


@patch("requests.Session.request")
def test_client_error_mapping_403(mock_req, test_config):
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.json.return_value = {"detail": "Action prohibited"}
    mock_req.return_value = mock_resp

    client = NexusClient(config=test_config)
    with pytest.raises(ForbiddenError) as exc_info:
        client.get("/api/admin")
    assert "Action prohibited" in str(exc_info.value)


@patch("requests.Session.request")
def test_client_error_mapping_404(mock_req, test_config):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"detail": "Device not found"}
    mock_req.return_value = mock_resp

    client = NexusClient(config=test_config)
    with pytest.raises(NotFoundError) as exc_info:
        client.get("/api/devices/999")
    assert "Device not found" in str(exc_info.value)


@patch("requests.Session.request", side_effect=requests.exceptions.Timeout("Read timeout"))
def test_client_timeout_handling(mock_req, test_config):
    client = NexusClient(config=test_config)
    with pytest.raises(TimeoutError) as exc_info:
        client.get("/api/slow")
    assert "timed out" in str(exc_info.value)


@patch("requests.Session.request", side_effect=requests.exceptions.ConnectionError("Refused"))
def test_client_connection_error_handling(mock_req, test_config):
    client = NexusClient(config=test_config)
    with pytest.raises(NetworkError) as exc_info:
        client.get("/api/down")
    assert "Could not connect to NEXUS" in str(exc_info.value)
