"""System diagnostics and health check engine for NEXUS CLI."""

import os
import platform
import sys
import time
from typing import Any, Dict, List

import requests
import typer
from rich.table import Table

from nexus_cli import __version__
from nexus_cli.client import get_client
from nexus_cli.config import CredentialStore, get_config_path, load_config
from nexus_cli.ui import console, output_json, set_json_mode


def run_diagnostics() -> Dict[str, Any]:
    """Execute all diagnostic probes and return structured results."""
    config = load_config()
    checks: List[Dict[str, Any]] = []

    # 1. CLI and Python Runtime
    checks.append({
        "category": "Runtime",
        "name": "CLI Version",
        "status": "pass",
        "detail": f"nexus v{__version__}",
    })
    checks.append({
        "category": "Runtime",
        "name": "Python Environment",
        "status": "pass",
        "detail": f"Python {platform.python_version()} ({sys.executable})",
    })

    # 2. Keyring / Credential Store
    keyring_enabled = CredentialStore.is_keyring_enabled()
    backend_name = "None (disabled or unavailable)"
    if keyring_enabled:
        try:
            import keyring
            backend_name = keyring.get_keyring().__class__.__name__
        except Exception:
            backend_name = "Unknown"

    checks.append({
        "category": "Security",
        "name": "Credential Store",
        "status": "pass" if keyring_enabled else "warn",
        "detail": f"Backend: {backend_name}" if keyring_enabled else "OS Keyring disabled/unavailable; fallback to chmod 0600 file",
    })

    # 3. Configuration File
    cfg_path = get_config_path()
    if cfg_path.exists():
        mode = oct(cfg_path.stat().st_mode & 0o777)
        is_secure = mode in ("0o600", "0o400") or platform.system() == "Windows"
        checks.append({
            "category": "Configuration",
            "name": "Config File",
            "status": "pass" if is_secure else "warn",
            "detail": f"{cfg_path} (mode: {mode})",
        })
    else:
        checks.append({
            "category": "Configuration",
            "name": "Config File",
            "status": "pass",
            "detail": f"Not found at {cfg_path} (using in-memory defaults)",
        })

    # 4. Authentication State
    has_token = bool(config.token)
    has_node_key = bool(config.node_api_key)
    checks.append({
        "category": "Authentication",
        "name": "User Session",
        "status": "pass" if has_token else "warn",
        "detail": f"Logged in as {config.email}" if (has_token and config.email) else ("Token set (no email)" if has_token else "Not logged in"),
    })
    checks.append({
        "category": "Authentication",
        "name": "Node Claim",
        "status": "pass" if (config.node_id and has_node_key) else "warn",
        "detail": f"Node ID #{config.node_id} (API key registered)" if (config.node_id and has_node_key) else "Node not claimed",
    })

    # 5. Core Node Connectivity
    api_url = config.api_url.rstrip("/")
    core_status = "fail"
    core_detail = f"Could not connect to {api_url}"
    try:
        t0 = time.perf_counter()
        resp = requests.get(f"{api_url}/health", timeout=3)
        latency = (time.perf_counter() - t0) * 1000
        if resp.status_code == 200:
            core_status = "pass"
            data = resp.json()
            core_detail = f"Online ({latency:.1f}ms) — {data.get('service', 'Core')} v{data.get('version', '?')} [{data.get('mode', 'local')}]"
        else:
            core_status = "fail"
            core_detail = f"HTTP {resp.status_code} from {api_url}/health"
    except Exception as e:
        core_detail = f"Unreachable at {api_url}: {e}"

    checks.append({
        "category": "Connectivity",
        "name": "Local Core Node",
        "status": core_status,
        "detail": core_detail,
    })

    # 6. Control Plane Connectivity
    cp_url = (config.control_plane_url or "").rstrip("/")
    if cp_url:
        cp_status = "fail"
        cp_detail = f"Could not connect to {cp_url}"
        try:
            t0 = time.perf_counter()
            resp = requests.get(f"{cp_url}/health", timeout=5)
            latency = (time.perf_counter() - t0) * 1000
            if resp.status_code == 200:
                cp_status = "pass"
                data = resp.json()
                cp_detail = f"Online ({latency:.1f}ms) — mode: {data.get('mode', 'control-plane')}"
            else:
                cp_status = "warn"
                cp_detail = f"HTTP {resp.status_code} from {cp_url}/health"
        except Exception as e:
            cp_status = "warn"
            cp_detail = f"Unreachable ({e})"
        checks.append({
            "category": "Connectivity",
            "name": "Control Plane",
            "status": cp_status,
            "detail": cp_detail,
        })

    # 7. Local Services
    # Faster Whisper STT
    try:
        import faster_whisper  # noqa: F401
        stt_status = "pass"
        stt_detail = "Installed (faster-whisper)"
    except ImportError:
        stt_status = "info"
        stt_detail = "Not installed (run 'nexus services install stt' to enable)"
    checks.append({
        "category": "Services",
        "name": "Speech-to-Text",
        "status": stt_status,
        "detail": stt_detail,
    })

    # Ollama LLM
    try:
        resp = requests.get("http://127.0.0.1:11434/api/version", timeout=0.5)
        if resp.status_code == 200:
            llm_status = "pass"
            llm_detail = f"Online (Ollama v{resp.json().get('version', '?')})"
        else:
            llm_status = "info"
            llm_detail = "Offline (Ollama returned non-200)"
    except Exception:
        llm_status = "info"
        llm_detail = "Offline / not running at http://127.0.0.1:11434"
    checks.append({
        "category": "Services",
        "name": "Local LLM",
        "status": llm_status,
        "detail": llm_detail,
    })

    # Overall calculation
    has_fail = any(c["status"] == "fail" for c in checks)
    has_warn = any(c["status"] == "warn" for c in checks)
    overall = "unhealthy" if has_fail else ("degraded" if has_warn else "healthy")

    return {
        "status": overall,
        "checks": checks,
    }


def doctor_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Diagnose NEXUS CLI environment, configuration, connectivity, and dependencies."""
    set_json_mode(json_output)
    report = run_diagnostics()

    output_json(report)
    if json_output:
        return

    table = Table(
        title=f"[bold]NEXUS Doctor Diagnostic Report — {report['status'].upper()}[/bold]",
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("Category", style="dim", width=16)
    table.add_column("Component", style="bold", width=22)
    table.add_column("Status", width=10, justify="center")
    table.add_column("Details")

    status_badges = {
        "pass": "[bold green]PASS[/bold green]",
        "warn": "[bold yellow]WARN[/bold yellow]",
        "fail": "[bold red]FAIL[/bold red]",
        "info": "[bold blue]INFO[/bold blue]",
    }

    for c in report["checks"]:
        badge = status_badges.get(c["status"], c["status"])
        table.add_row(c["category"], c["name"], badge, c["detail"])

    console.print(table)
