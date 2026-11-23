"""Services management subcommands: STT, LLM, bootstrap."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel

from nexus_cli.client import get_client
from nexus_cli.config import load_config
from nexus_cli.errors import ExitCode
from nexus_cli.ui import console, output_json, set_json_mode

services_app = typer.Typer(name="services", help="Manage optional services on this node (STT, LLM, bootstrap)")


def detect_local_services() -> dict:
    """Probe the local machine for installable services without network calls."""
    services = {}
    try:
        import faster_whisper  # noqa: F401
        services["stt"] = "faster-whisper"
    except ImportError:
        pass
    try:
        import requests as _r
        try:
            _r.get("http://127.0.0.1:11434/api/version", timeout=0.5)
            services["llm"] = "ollama"
        except Exception:
            pass
    except ImportError:
        pass
    return services


@services_app.command("status")
def services_status(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Show which optional services this machine's node has installed."""
    set_json_mode(json_output)
    config = load_config()

    services = {}
    if config.node_id and config.control_plane_url:
        try:
            client = get_client()
            resp = client.get(f"{config.control_plane_url.rstrip('/')}/api/nodes", timeout=10)
            mine = [n for n in resp.json() if n.get("id") == config.node_id]
            services = mine[0].get("services", {}) if mine else {}
        except Exception:
            services = detect_local_services()
    else:
        services = detect_local_services()

    output_json(services)
    if json_output:
        return

    rows = "\n".join(f"[cyan]{k}[/cyan]: {v}" for k, v in services.items()) or "[dim]none installed[/dim]"
    console.print(Panel(rows, title="Node services", border_style="cyan", expand=False))


@services_app.command("install")
def services_install(
    service: str = typer.Argument(..., help="Service to install: stt | llm | bootstrap (full environment setup)"),
    mirror: str = typer.Option(
        "default",
        help="PyPI mirror for this install: default | tuna | aliyun | ustc | sjtu | https:// URL.",
    ),
) -> None:
    """Install an optional service on this machine (the main node)."""
    config = load_config()

    if service == "bootstrap":
        core_api_path = Path(__file__).resolve().parents[3] / "services" / "core-api"
        if str(core_api_path) not in sys.path:
            sys.path.insert(0, str(core_api_path))
        try:
            from nexus_core.bootstrap import plan_bootstrap, run_bootstrap
        except ImportError as e:
            console.print(
                Panel(f"Bootstrap unavailable.\n[dim]{e}[/dim]", title="[bold red]Error[/bold red]", border_style="red", expand=False)
            )
            raise typer.Exit(ExitCode.FAILURE)

        try:
            plan = plan_bootstrap(mirror=mirror)
        except ValueError as e:
            console.print(Panel(str(e), title="[bold red]Bad mirror[/bold red]", border_style="red", expand=False))
            raise typer.Exit(ExitCode.USAGE_ERROR)

        console.print(Panel(plan.describe(), title="[bold cyan]Setup plan[/bold cyan]", border_style="cyan", expand=False))
        if not run_bootstrap(plan, echo=lambda line: console.print(f"[dim]{line}[/dim]")):
            console.print(Panel("Setup failed — see output above.", title="[bold red]Setup failed[/bold red]", border_style="red", expand=False))
            raise typer.Exit(ExitCode.FAILURE)

        console.print(
            Panel(
                f"Environment ready. Node start command:\n  {plan.python_bin} -m uvicorn nexus_core.main:app",
                title="[bold green]Setup complete[/bold green]",
                border_style="green",
                expand=False,
            )
        )
        return

    if service == "stt":
        console.print(Panel("Installing [bold cyan]faster-whisper[/bold cyan] (reliable local transcription)...", border_style="cyan", expand=False))
        result = subprocess.run([sys.executable, "-m", "pip", "install", "faster-whisper"])
        if result.returncode != 0:
            console.print(Panel("pip install failed.", title="[bold red]Install failed[/bold red]", border_style="red", expand=False))
            raise typer.Exit(ExitCode.FAILURE)
        console.print(Panel("faster-whisper installed successfully.", title="[bold green]STT installed[/bold green]", border_style="green", expand=False))
    elif service == "llm":
        console.print(
            Panel(
                "Ollama is a native app, not a pip package.\n"
                "Install from https://ollama.com/download then:\n"
                "  ollama pull llama3.2\n"
                "The node auto-detects it at http://127.0.0.1:11434.",
                title="Install Ollama",
                border_style="cyan",
                expand=False,
            )
        )
    else:
        console.print(Panel(f"Unknown service '{service}'. Available: stt, llm, bootstrap.", title="[bold red]Unknown service[/bold red]", border_style="red", expand=False))
        raise typer.Exit(ExitCode.USAGE_ERROR)

    # Report to control plane if claimed node
    if config.node_id and config.control_plane_url:
        detected = detect_local_services()
        try:
            client = get_client()
            client.post(
                f"{config.control_plane_url.rstrip('/')}/api/nodes/{config.node_id}/services",
                json={"services": detected},
                timeout=10,
            )
        except Exception:
            pass
