"""High-performance API client for NEXUS Core and Control Plane."""

import os
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import CLIConfig, load_config
from .errors import (
    AuthenticationError,
    ConfigurationError,
    ForbiddenError,
    NetworkError,
    NotFoundError,
    TimeoutError,
)


class NexusClient:
    """Robust, typed HTTP client with retries, pooling, and token refresh."""

    def __init__(self, config: Optional[CLIConfig] = None, base_url: Optional[str] = None):
        self.config = config or load_config()
        if not isinstance(base_url, str):
            base_url = None
        self.base_url = (base_url or self.config.api_url).rstrip("/")
        self.session = requests.Session()

        # Resilient connection pool and retry policy
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "nexus-cli/0.2.0",
        }
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        if self.config.node_api_key:
            headers["X-Node-API-Key"] = self.config.node_api_key
        if custom_headers:
            headers.update(custom_headers)
        return headers

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        allow_refresh: bool = True,
    ) -> requests.Response:
        url = path if path.startswith(("http://", "https://")) else f"{self.base_url}{path}"
        req_headers = self._headers(headers)
        req_timeout = timeout or self.config.timeout

        try:
            resp = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=req_headers,
                timeout=req_timeout,
            )
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Request to {url} timed out after {req_timeout}s.", details=str(e))
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Could not connect to NEXUS at {self.base_url}.", details=str(e))
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error communicating with {url}.", details=str(e))

        # Handle 401 and attempt automatic token rotation if refresh token is present
        if resp.status_code == 401 and allow_refresh and self.config.refresh_token:
            if self._attempt_token_refresh():
                return self.request(
                    method=method,
                    path=path,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=timeout,
                    allow_refresh=False,
                )

        # Map HTTP errors to typed exceptions
        if resp.status_code == 401:
            detail = self._extract_detail(resp) or "Authentication failed. Session expired or invalid."
            raise AuthenticationError(detail)
        elif resp.status_code == 403:
            detail = self._extract_detail(resp) or "Access forbidden. Insufficient permissions."
            raise ForbiddenError(detail)
        elif resp.status_code == 404:
            detail = self._extract_detail(resp) or f"Resource at {path} not found."
            raise NotFoundError(detail)
        elif resp.status_code >= 400:
            detail = self._extract_detail(resp) or f"Request failed with HTTP {resp.status_code}"
            from .errors import NexusError
            raise NexusError(detail, exit_code=1)

        return resp

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)

    def _attempt_token_refresh(self) -> bool:
        """Attempt transparent token rotation via refresh endpoint."""
        refresh_url = f"{self.base_url}/api/auth/refresh"
        try:
            r = self.session.post(
                refresh_url,
                json={"refresh_token": self.config.refresh_token},
                timeout=5,
            )
            if r.status_code == 200:
                data = r.json()
                self.config.token = data.get("access_token")
                if data.get("refresh_token"):
                    self.config.refresh_token = data.get("refresh_token")
                from .config import save_config
                save_config(self.config)
                return True
        except Exception:
            pass
        return False

    def _extract_detail(self, resp: requests.Response) -> Optional[str]:
        try:
            data = resp.json()
            if isinstance(data, dict):
                return data.get("detail") or data.get("message")
        except Exception:
            pass
        return resp.text.strip() if resp.text else None


def get_client(config: Optional[CLIConfig] = None, base_url: Optional[str] = None) -> NexusClient:
    return NexusClient(config=config, base_url=base_url)
