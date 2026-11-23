"""Status Header Widget displaying real system telemetry, auth state, and connectivity."""

import time
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static

from ...client import get_client
from ...config import load_config
from ... import __version__


class StatusHeader(Static):
    """Header widget showing identity, connection status, latency, and active profile."""

    is_online: reactive[bool] = reactive(False)
    ping_ms: reactive[int] = reactive(0)
    user_identity: reactive[str] = reactive("Guest / Unauthenticated")
    active_profile: reactive[str] = reactive("default")
    api_endpoint: reactive[str] = reactive("https://nexus-control-plane-uvi8.onrender.com")

    def compose(self) -> ComposeResult:
        with Container(id="nexus-status-header"):
            with Horizontal(classes="header-top-row"):
                yield Label("▲ NEXUS CONTROL CENTER", id="nexus-brand")
                with Horizontal(id="header-stats"):
                    yield Label(f"v{__version__}", id="header-version", classes="stat-badge")
                    yield Label(f"Profile: {self.active_profile}", id="header-profile", classes="stat-badge-active")
                    yield Label(
                        "● CHECKING...",
                        id="header-status-pill",
                        classes="stat-badge",
                    )
            with Horizontal(classes="header-bottom-row"):
                yield Label(f"User: {self.user_identity}", id="header-user", classes="header-meta-item")
                yield Label(f"Endpoint: {self.api_endpoint}", id="header-endpoint", classes="header-meta-item")
                yield Label(f"Ping: {self.ping_ms}ms", id="header-ping", classes="header-meta-item")

    def on_mount(self) -> None:
        self.refresh_telemetry()
        self.set_interval(15.0, self.refresh_telemetry)

    def refresh_telemetry(self) -> None:
        """Query real backend API for connectivity and auth status."""
        cfg = load_config()
        self.active_profile = cfg.active_profile
        self.api_endpoint = cfg.api_url
        if cfg.email:
            self.user_identity = cfg.email
        elif cfg.token:
            self.user_identity = "Authenticated Operator"
        else:
            self.user_identity = "Guest / Not Logged In"

        start_t = time.perf_counter()
        try:
            client = get_client()
            resp = client.get("/health", timeout=3)
            elapsed = int((time.perf_counter() - start_t) * 1000)
            if resp.status_code == 200:
                self.is_online = True
                self.ping_ms = elapsed
            else:
                self.is_online = False
                self.ping_ms = elapsed
        except Exception:
            self.is_online = False
            self.ping_ms = 0

        self._update_badges()

    def _update_badges(self) -> None:
        try:
            pill = self.query_one("#header-status-pill", Label)
            if self.is_online:
                pill.update("● ONLINE")
                pill.remove_class("stat-badge-offline")
                pill.remove_class("stat-badge")
                pill.add_class("stat-badge-online")
            else:
                pill.update("● OFFLINE")
                pill.remove_class("stat-badge-online")
                pill.remove_class("stat-badge")
                pill.add_class("stat-badge-offline")

            self.query_one("#header-profile", Label).update(f"Profile: {self.active_profile}")
            self.query_one("#header-user", Label).update(f"User: {self.user_identity}")
            self.query_one("#header-endpoint", Label).update(f"Endpoint: {self.api_endpoint}")
            self.query_one("#header-ping", Label).update(f"Ping: {self.ping_ms}ms" if self.is_online else "Ping: --")
        except Exception:
            pass
