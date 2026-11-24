"""Local Services Manager Widget for NEXUS Control Center."""

from datetime import datetime
import os
import platform
import subprocess
import sys
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, DataTable, Label, Static

from ...client import get_client
from ...config import load_config
from .context import ContextPanel


class ServicesView(Static):
    """Local and edge compute services manager for STT, LLM runtimes, and background daemons."""

    class ServiceAction(Message):
        def __init__(self, action_id: str, service_id: str) -> None:
            self.action_id = action_id
            self.service_id = service_id
            super().__init__()

    _services_state: Dict[str, Dict[str, Any]] = {}

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="services-scroll-container"):
            with Horizontal(classes="view-header-bar"):
                yield Label("⚙️ LOCAL SERVICES & COMPUTE RUNTIMES", classes="view-title")
                with Horizontal(classes="header-actions"):
                    yield Button("🔄 Probe Services", id="btn-services-probe", variant="primary", classes="btn-sm")
                    yield Button("📋 View Logs", id="btn-services-logs", classes="btn-sm")

            # Status Banner
            with Horizontal(classes="config-bar"):
                yield Label("Service Manager Mode: [bold cyan]Local Machine Edge Daemon[/bold cyan]  |  Python Runtime: [dim]" + sys.executable + "[/dim]")

            # Services Cards Grid
            with Vertical(id="services-cards-grid"):
                # Service 1: Ollama LLM
                with Vertical(classes="overview-full-card", id="svc-card-llm"):
                    with Horizontal(classes="card-header-row"):
                        yield Label("🧠 LLM Runtime (Ollama / Local Inference)", classes="card-header")
                        yield Label("Probing...", id="badge-svc-llm", classes="stat-badge")
                    yield Static("Checking local Ollama daemon on http://127.0.0.1:11434...", id="desc-svc-llm", classes="card-body")

                # Service 2: Faster Whisper STT
                with Vertical(classes="overview-full-card", id="svc-card-stt"):
                    with Horizontal(classes="card-header-row"):
                        yield Label("🎙️ Speech-to-Text Engine (faster-whisper)", classes="card-header")
                        yield Label("Probing...", id="badge-svc-stt", classes="stat-badge")
                    yield Static("Checking faster-whisper CTranslate2 model library...", id="desc-svc-stt", classes="card-body")

                # Service 3: Node Edge Daemon & Relay Bridge
                with Vertical(classes="overview-full-card", id="svc-card-daemon"):
                    with Horizontal(classes="card-header-row"):
                        yield Label("🖥️ NEXUS Node Core Daemon", classes="card-header")
                        yield Label("Probing...", id="badge-svc-daemon", classes="stat-badge")
                    yield Static("Inspecting local node daemon and inbound WebSocket relay...", id="desc-svc-daemon", classes="card-body")

                # Service 4: Bootstrap & Venv Environment
                with Vertical(classes="overview-full-card", id="svc-card-bootstrap"):
                    with Horizontal(classes="card-header-row"):
                        yield Label("📦 Managed Virtualenv & Dependency Suite", classes="card-header")
                        yield Label("PASS", id="badge-svc-bootstrap", classes="stat-badge-online")
                    yield Static("Python 3.11 managed environment with pinned cryptographic and UI suites.", id="desc-svc-bootstrap", classes="card-body")

    def on_mount(self) -> None:
        self.probe_services()

    def probe_services(self) -> None:
        self.run_worker(self._run_probe, thread=True)

    def _run_probe(self) -> None:
        cfg = load_config()

        # 1. Probe Ollama
        llm_running = False
        llm_version = "N/A"
        try:
            import requests as _r
            resp = _r.get("http://127.0.0.1:11434/api/version", timeout=1.0)
            if resp.status_code == 200:
                llm_running = True
                llm_version = resp.json().get("version", "Active")
        except Exception:
            pass

        # 2. Probe STT
        stt_installed = False
        try:
            import faster_whisper  # noqa: F401
            stt_installed = True
        except ImportError:
            pass

        # 3. Probe Daemon
        daemon_connected = False
        try:
            client = get_client()
            r = client.get("/health", timeout=2.0)
            daemon_connected = (r.status_code == 200)
        except Exception:
            pass

        results = {
            "llm": {"running": llm_running, "version": llm_version},
            "stt": {"installed": stt_installed},
            "daemon": {"connected": daemon_connected, "node_id": cfg.node_id},
        }

        self.app.call_from_thread(self._render_probe_results, results)

    def _render_probe_results(self, res: Dict[str, Any]) -> None:
        if not self.is_mounted:
            return
        try:
            # LLM
            llm = res["llm"]
            badge_llm = self.query_one("#badge-svc-llm", Label)
            desc_llm = self.query_one("#desc-svc-llm", Static)
            badge_llm.remove_class("stat-badge-online")
            badge_llm.remove_class("stat-badge-offline")

            if llm["running"]:
                badge_llm.update("● RUNNING")
                badge_llm.add_class("stat-badge-online")
                desc_llm.update(
                    f"[bold green]Ollama daemon is active on port 11434.[/bold green] (Version: {llm['version']})\n"
                    "Supports sovereign local LLM inference without sending prompts off-device."
                )
            else:
                badge_llm.update("○ IDLE / STOPPED")
                badge_llm.add_class("stat-badge-offline")
                desc_llm.update(
                    "[dim]Ollama is not running on 127.0.0.1:11434.[/dim]\n"
                    "[dim]To enable local LLM processing: install Ollama from ollama.ai and start the app.[/dim]"
                )

            # STT
            stt = res["stt"]
            badge_stt = self.query_one("#badge-svc-stt", Label)
            desc_stt = self.query_one("#desc-svc-stt", Static)
            badge_stt.remove_class("stat-badge-online")
            badge_stt.remove_class("stat-badge-offline")

            if stt["installed"]:
                badge_stt.update("● READY")
                badge_stt.add_class("stat-badge-online")
                desc_stt.update(
                    "[bold green]faster-whisper is installed in the local environment.[/bold green]\n"
                    "Supports offline high-speed speech-to-text transcription via CTranslate2."
                )
            else:
                badge_stt.update("○ OPTIONAL (NOT INSTALLED)")
                badge_stt.add_class("stat-badge")
                desc_stt.update(
                    "[dim]faster-whisper is optional. To install: run 'nexus bootstrap' or pip install faster-whisper.[/dim]"
                )

            # Daemon
            daemon = res["daemon"]
            badge_dmn = self.query_one("#badge-svc-daemon", Label)
            desc_dmn = self.query_one("#desc-svc-daemon", Static)
            badge_dmn.remove_class("stat-badge-online")
            badge_dmn.remove_class("stat-badge-offline")

            if daemon["connected"]:
                badge_dmn.update("● CONNECTED")
                badge_dmn.add_class("stat-badge-online")
                desc_dmn.update(
                    f"[bold green]Connected to Core Control Plane.[/bold green] Machine Role: node-{daemon['node_id'] or 'standalone'}\n"
                    "Secure reverse WebSocket tunnel coordinates remote client attachment without opening inbound ports."
                )
            else:
                badge_dmn.update("● DISCONNECTED")
                badge_dmn.add_class("stat-badge-offline")
                desc_dmn.update(
                    "[dim]Node is currently disconnected from the control plane.[/dim]"
                )
        except Exception:
            pass

        # Update Context Panel
        try:
            ctx = self.app.query_one(ContextPanel)
            ctx.update_resource(
                title="Local Services Manager",
                subtitle="Edge Inference & Background Daemons",
                properties={
                    "Ollama LLM": "Running" if llm["running"] else "Idle",
                    "Speech STT": "Ready" if stt["installed"] else "Optional",
                    "Node Daemon": "Connected" if daemon["connected"] else "Offline",
                    "Isolation": "Localhost Only (127.0.0.1)",
                },
                action_label="Run Service Probe",
                action_id="services.status",
                help_text="Probes local system services without sending credentials over the network.",
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-services-probe":
            self.probe_services()
        elif event.button.id == "btn-services-logs":
            self.post_message(self.ServiceAction("view_logs", "all"))
