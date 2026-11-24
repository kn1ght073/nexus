"""Status Header Widget displaying real system telemetry, auth state, and connectivity."""

from datetime import datetime
import time
from typing import List

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static

from ...client import get_client
from ...config import load_config, mask_email_address, validate_session
from ... import __version__


class StatusHeader(Static):
    """Header widget showing identity, connection status, latency, and active profile."""

    is_online: reactive[bool] = reactive(False)
    connection_status: reactive[str] = reactive("UNKNOWN")
    ping_ms: reactive[int] = reactive(0)
    ping_avg: reactive[int] = reactive(0)
    ping_min: reactive[int] = reactive(0)
    ping_max: reactive[int] = reactive(0)
    user_identity: reactive[str] = reactive("Guest / Unauthenticated")
    active_profile: reactive[str] = reactive("default")
    api_endpoint: reactive[str] = reactive("https://nexus-control-plane-uvi8.onrender.com")
    local_node: reactive[str] = reactive("unclaimed")
    last_checked_time: reactive[str] = reactive("--:--:--")

    _latency_history: List[int] = []

    def compose(self) -> ComposeResult:
        with Container(id="nexus-status-header"):
            with Horizontal(classes="header-top-row"):
                yield Label("▲ NEXUS CONTROL CENTER", id="nexus-brand")
                with Horizontal(id="header-stats"):
                    yield Label(f"v{__version__}", id="header-version", classes="stat-badge")
                    yield Label(f"Profile: {self.active_profile}", id="header-profile", classes="stat-badge-active")
                    yield Label(f"Node: {self.local_node}", id="header-node", classes="stat-badge")
                    yield Label(
                        "● CHECKING...",
                        id="header-status-pill",
                        classes="stat-badge",
                    )
            with Horizontal(classes="header-bottom-row"):
                yield Label(f"User: {self.user_identity}", id="header-user", classes="header-meta-item")
                yield Label(f"Endpoint: {self.api_endpoint}", id="header-endpoint", classes="header-meta-item")
                yield Label(f"Ping: {self.ping_ms}ms", id="header-ping", classes="header-meta-item")
                yield Label(f"Checked: {self.last_checked_time}", id="header-last-checked", classes="header-meta-item")

    def on_mount(self) -> None:
        self.refresh_telemetry()
        self.set_interval(15.0, self.refresh_telemetry)

    def refresh_telemetry(self) -> None:
        """Query real backend API for connectivity and auth status."""
        cfg = load_config()
        self.active_profile = cfg.active_profile
        self.api_endpoint = cfg.api_url
        self.local_node = f"node-{cfg.node_id}" if cfg.node_id else "local-standalone"

        # Validate active session against backend to ensure deleted accounts are purged
        user_info = validate_session()
        cfg = load_config()

        if user_info and not user_info.get("offline"):
            user_email = user_info.get("email") or cfg.email
            self.user_identity = mask_email_address(user_email) if cfg.mask_email else user_email
        elif user_info and user_info.get("offline"):
            user_email = cfg.email or "Cached Operator"
            display_email = mask_email_address(user_email) if cfg.mask_email else user_email
            self.user_identity = f"{display_email} (Offline)"
        else:
            self.user_identity = "Guest / Not Logged In"

        start_t = time.perf_counter()
        now_str = datetime.now().strftime("%H:%M:%S")
        self.last_checked_time = now_str

        try:
            client = get_client()
            resp = client.get("/health", timeout=3)
            elapsed = int((time.perf_counter() - start_t) * 1000)

            if resp.status_code == 200:
                self.is_online = True
                self.ping_ms = elapsed
                self._latency_history.append(elapsed)
                if len(self._latency_history) > 10:
                    self._latency_history.pop(0)

                self.ping_min = min(self._latency_history)
                self.ping_max = max(self._latency_history)
                self.ping_avg = sum(self._latency_history) // len(self._latency_history)

                if elapsed > 1000:
                    self.connection_status = "DEGRADED"
                else:
                    self.connection_status = "ONLINE"
            else:
                self.is_online = False
                self.connection_status = "DEGRADED"
                self.ping_ms = elapsed
        except Exception:
            self.is_online = False
            self.connection_status = "OFFLINE"
            self.ping_ms = 0

        self._update_badges()

    def _update_badges(self) -> None:
        try:
            pill = self.query_one("#header-status-pill", Label)
            pill.remove_class("stat-badge-online")
            pill.remove_class("stat-badge-offline")
            pill.remove_class("stat-badge-degraded")
            pill.remove_class("stat-badge")

            if self.connection_status == "ONLINE":
                pill.update("● ONLINE")
                pill.add_class("stat-badge-online")
            elif self.connection_status == "DEGRADED":
                pill.update("● DEGRADED")
                pill.add_class("stat-badge-degraded")
            else:
                pill.update("● OFFLINE")
                pill.add_class("stat-badge-offline")

            self.query_one("#header-profile", Label).update(f"Profile: {self.active_profile}")
            self.query_one("#header-node", Label).update(f"Node: {self.local_node}")
            self.query_one("#header-user", Label).update(f"User: {self.user_identity}")
            self.query_one("#header-endpoint", Label).update(f"Endpoint: {self.api_endpoint}")

            if self.is_online:
                ping_txt = f"Ping: {self.ping_ms}ms (avg {self.ping_avg}ms, min {self.ping_min}ms, max {self.ping_max}ms)"
            else:
                ping_txt = "Ping: -- (offline)"

            self.query_one("#header-ping", Label).update(ping_txt)
            self.query_one("#header-last-checked", Label).update(f"Checked: {self.last_checked_time}")
        except Exception:
            pass
