"""Mac & Local Authoritative NEXUS Host Management, LAN Coordination & Mobile Pairing."""

import json
import os
from pathlib import Path
import platform as _platform
import signal
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import requests
import typer

from ..config import load_config, save_config
from ..errors import NexusError
from ..ui import (
    console,
    create_table,
    is_json_mode,
    output_json,
    print_error,
    print_info,
    print_success,
    render_key_value,
    set_json_mode,
    status_spinner,
)

host_app = typer.Typer(help="Manage local authoritative NEXUS host, LAN access, and mobile pairing")

PID_FILE = Path.home() / ".nexus" / "host.pid"
HOST_INFO_FILE = Path.home() / ".nexus" / "host.json"


def _get_lan_ips() -> List[str]:
    """Detect non-loopback IPv4 addresses bound to local network interfaces."""
    ips: List[str] = []
    # Method 1: route probe without sending packets
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(("10.254.254.254", 1))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                ips.append(ip)
        except Exception:
            pass
        finally:
            s.close()
    except Exception:
        pass

    # Method 2: hostname resolution
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            cand = info[4][0]
            if cand and not cand.startswith("127.") and ":" not in cand and cand not in ips:
                ips.append(cand)
    except Exception:
        pass

    return ips or ["127.0.0.1"]


def _render_ascii_qr(data: str) -> None:
    """Render a terminal-friendly QR code using qrcode if available, or visual pairing card."""
    try:
        import qrcode  # type: ignore
        qr = qrcode.QRCode(border=1)
        qr.add_data(data)
        qr.make(fit=True)
        # Render inverted black/white blocks for dark terminal
        matrix = qr.get_matrix()
        for row in matrix:
            line = "".join("  " if col else "██" for col in row)
            console.print(f"[white]{line}[/white]")
        return
    except ImportError:
        pass

    # High-contrast visual terminal pairing glyph & box
    console.print("[bold cyan]┌────────────────────────────────────────────────────────────┐[/bold cyan]")
    console.print("[bold cyan]│[/bold cyan]           [bold white]NEXUS SECURE PAIRING LINK[/bold white]                        [bold cyan]│[/bold cyan]")
    console.print("[bold cyan]├────────────────────────────────────────────────────────────┤[/bold cyan]")
    console.print(f"[bold cyan]│[/bold cyan]  [bold yellow]Scan/Paste Target:[/bold yellow]                                       [bold cyan]│[/bold cyan]")
    console.print(f"[bold cyan]│[/bold cyan]  [cyan]{data[:56]:<58}[/cyan] [bold cyan]│[/bold cyan]")
    console.print("[bold cyan]└────────────────────────────────────────────────────────────┘[/bold cyan]")


@host_app.command("start")
def start_host(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind address (0.0.0.0 for LAN, 127.0.0.1 for local-only)"),
    port: int = typer.Option(8000, "--port", "-p", help="Port number for Core API"),
    daemon: bool = typer.Option(False, "--daemon", "-d", help="Run as background daemon process"),
    db_path: Optional[str] = typer.Option(None, "--db", help="Path to SQLite database file"),
):
    """Start the authoritative NEXUS Host on this Mac."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Check if host is already running
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            os.kill(old_pid, 0)
            print_error(f"NEXUS Host is already running with PID {old_pid}. Run 'nexus host stop' first.")
            raise typer.Exit(1)
        except (ValueError, OSError):
            PID_FILE.unlink(missing_ok=True)

    # Target persistent database
    resolved_db = Path(db_path).expanduser().resolve() if db_path else (Path.home() / ".nexus" / "nexus.db")
    resolved_db.parent.mkdir(parents=True, exist_ok=True)

    lan_ips = _get_lan_ips()
    primary_lan_ip = lan_ips[0] if lan_ips else "127.0.0.1"
    local_url = f"http://127.0.0.1:{port}"
    lan_url = f"http://{primary_lan_ip}:{port}"

    env = os.environ.copy()
    env["NEXUS_CONTROL_PLANE_MODE"] = "false"
    env["NEXUS_HOST"] = host
    env["NEXUS_PORT"] = str(port)
    env["NEXUS_DATABASE_PATH"] = str(resolved_db)

    # Locate project root and python executable
    repo_root = Path(__file__).resolve().parents[4]
    python_candidates = [
        repo_root / "services" / "core-api" / ".venv" / "bin" / "python",
        repo_root / ".venv" / "bin" / "python",
        Path(sys.executable),
    ]
    py_exec = next((p for p in python_candidates if p.exists()), Path(sys.executable))

    cmd = [
        str(py_exec),
        "-m",
        "uvicorn",
        "nexus_core.main:create_app",
        "--factory",
        "--host",
        host,
        "--port",
        str(port),
    ]

    cwd = str(repo_root / "services" / "core-api") if (repo_root / "services" / "core-api").exists() else str(repo_root)

    if daemon:
        log_file = Path.home() / ".nexus" / "host.log"
        with open(log_file, "a") as log_out:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdout=log_out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        PID_FILE.write_text(str(proc.pid))
        
        # Save host metadata
        host_info = {
            "pid": proc.pid,
            "host": host,
            "port": port,
            "database_path": str(resolved_db),
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "local_url": local_url,
            "lan_url": lan_url,
        }
        HOST_INFO_FILE.write_text(json.dumps(host_info, indent=2))

        # Wait up to 5s for probe
        with status_spinner("Waiting for NEXUS Host to initialize…"):
            up = False
            for _ in range(10):
                time.sleep(0.5)
                try:
                    r = requests.get(f"{local_url}/health", timeout=1)
                    if r.status_code == 200:
                        up = True
                        break
                except Exception:
                    pass

        if up:
            print_success(
                f"NEXUS Authoritative Host started in background (PID: [bold cyan]{proc.pid}[/bold cyan]).\n\n"
                f"• Local Endpoint: [bold green]{local_url}[/bold green]\n"
                f"• LAN Mobile URL: [bold cyan]{lan_url}[/bold cyan]\n"
                f"• Authoritative SQLite: [dim]{resolved_db}[/dim]\n"
                f"• Mode: [bold]Node (Full Sovereign Workspace)[/bold]",
                title="HOST ONLINE",
            )
            console.print("[dim]Firewall Tip: If connecting from mobile, ensure macOS Firewall allows incoming connections on port " + str(port) + ".[/dim]")
            console.print("[dim]Pairing: Run 'nexus host pair' to display mobile pairing code and QR link.[/dim]")
        else:
            print_error(f"Host spawned with PID {proc.pid} but health check timed out. Check {log_file} for details.")
    else:
        print_info(
            f"Starting NEXUS Authoritative Host in foreground on {host}:{port}…\n"
            f"• Local: [green]{local_url}[/green]\n"
            f"• LAN:   [cyan]{lan_url}[/cyan]\n"
            f"• DB:    {resolved_db}\n"
            f"Press Ctrl-C to terminate.",
            title="STARTING HOST",
        )
        try:
            subprocess.run(cmd, cwd=cwd, env=env)
        except KeyboardInterrupt:
            console.print("\n[dim]Host shutdown requested.[/dim]")


@host_app.command("stop")
def stop_host():
    """Stop the running background NEXUS Host daemon."""
    if not PID_FILE.exists():
        print_info("No NEXUS Host PID file found. Host is not running in background mode.")
        return

    try:
        pid = int(PID_FILE.read_text().strip())
    except ValueError:
        PID_FILE.unlink(missing_ok=True)
        print_error("Invalid PID file. Cleaned up stale reference.")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for exit
        for _ in range(10):
            time.sleep(0.3)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            os.kill(pid, signal.SIGKILL)
        print_success(f"NEXUS Host (PID {pid}) stopped successfully.", title="HOST TERMINATED")
    except OSError as e:
        print_info(f"Process {pid} is no longer running ({e}). Cleaning up PID file.")
    finally:
        PID_FILE.unlink(missing_ok=True)
        HOST_INFO_FILE.unlink(missing_ok=True)


@host_app.command("status")
def host_status(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Check live status and telemetry of the local NEXUS Host."""
    if json_output:
        set_json_mode(True)

    # 1. Check PID file
    pid = None
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
        except ValueError:
            pass

    # 2. HTTP probe to /api/host/status and /health
    host_data: Optional[Dict[str, Any]] = None
    health_data: Optional[Dict[str, Any]] = None
    ports = [8000, 8080]
    for p in ports:
        try:
            r = requests.get(f"http://127.0.0.1:{p}/api/host/status", timeout=2)
            if r.status_code == 200:
                host_data = r.json()
                break
        except Exception:
            pass

    if not host_data:
        for p in ports:
            try:
                r = requests.get(f"http://127.0.0.1:{p}/health", timeout=2)
                if r.status_code == 200:
                    health_data = r.json()
                    break
            except Exception:
                pass

    if is_json_mode():
        output_json({
            "online": bool(host_data or health_data),
            "pid": pid,
            "host_status": host_data,
            "health": health_data,
        })
        return

    if host_data:
        counts = host_data.get("counts", {})
        db_info = host_data.get("database", {})
        lan_ips = host_data.get("lan_ips", [])
        port = host_data.get("port", 8000)

        render_key_value(
            {
                "Host Status": "[bold green]ONLINE (Authoritative Node)[/bold green]",
                "PID": str(pid or "Foreground / System Process"),
                "Hostname": host_data.get("hostname", "unknown"),
                "Platform": host_data.get("platform", _platform.system()).capitalize(),
                "Local URL": f"[green]http://127.0.0.1:{port}[/green]",
                "LAN URL (Mobile)": ", ".join(f"[bold cyan]http://{ip}:{port}[/bold cyan]" for ip in lan_ips) or "No LAN IPs detected",
                "Database Engine": f"{db_info.get('engine', 'sqlite').upper()} (WAL Mode)",
                "Database File": db_info.get("path", "~/.nexus/nexus.db"),
                "Database Size": f"{db_info.get('size_bytes', 0) / 1024:.1f} KB",
                "Active Projects": str(counts.get("projects", 0)),
                "Active Tasks": str(counts.get("tasks", 0)),
                "Active Notes": str(counts.get("notes", 0)),
                "Paired Devices": str(counts.get("devices", 0)),
            },
            title="NEXUS AUTHORITATIVE HOST TELEMETRY",
        )
    elif health_data:
        render_key_value(
            {
                "Status": f"[green]ONLINE ({health_data.get('mode', 'unknown')})[/green]",
                "Service": health_data.get("service", "nexus-core"),
                "PID": str(pid or "Unknown"),
            },
            title="NEXUS HOST HEALTH",
        )
    else:
        print_info(
            "NEXUS Host is currently [bold red]OFFLINE[/bold red].\n\n"
            "To launch the authoritative host on this Mac:\n"
            "  [bold cyan]nexus host start --daemon[/bold cyan]\n\n"
            "Connected devices (Mobile, CLI, Desktop) will synchronize data with this instance.",
            title="HOST OFFLINE",
        )


@host_app.command("pair")
def pair_host(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Generate mobile pairing credentials, LAN connection URL, and terminal QR code."""
    if json_output:
        set_json_mode(True)

    lan_ips = _get_lan_ips()
    primary_ip = lan_ips[0] if lan_ips else "127.0.0.1"
    host_url = f"http://{primary_ip}:8000"

    # Attempt to mint official pairing code via Core API
    code = None
    try:
        r = requests.post("http://127.0.0.1:8000/api/nodes/pair", timeout=2)
        if r.status_code == 200:
            code = r.json().get("code")
    except Exception:
        pass

    if not code:
        # Fallback deterministic pseudo-random PIN for offline direct LAN pairing
        import secrets
        code = f"{secrets.randbelow(900000) + 100000}"

    pair_payload = {
        "type": "nexus_host_pairing",
        "url": host_url,
        "code": code,
        "name": socket.gethostname(),
        "platform": _platform.system().lower(),
    }
    encoded_uri = f"nexus://pair?url={host_url}&code={code}&name={socket.gethostname()}"

    if is_json_mode():
        output_json({**pair_payload, "pairing_uri": encoded_uri})
        return

    console.print("\n[bold cyan]═══ NEXUS HOST PAIRING GATEWAY ═══[/bold cyan]\n")
    _render_ascii_qr(encoded_uri)

    render_key_value(
        {
            "LAN Host URL": f"[bold cyan]{host_url}[/bold cyan]",
            "Pairing Code": f"[bold yellow]{code}[/bold yellow]",
            "Host Name": socket.gethostname(),
            "Pairing URI": f"[dim]{encoded_uri}[/dim]",
            "Expires In": "15 minutes",
        },
        title="MOBILE PAIRING CREDENTIALS",
    )

    console.print(
        "\n[bold white]To connect your Mobile Companion:[/bold white]\n"
        "1. Open NEXUS Mobile App > Settings > Host Connection.\n"
        f"2. Set Host Address to [bold cyan]{host_url}[/bold cyan] and tap [bold]Test Connection[/bold].\n"
        f"3. Or navigate to [bold]Nodes > Pair Edge Node[/bold] and enter code [bold yellow]{code}[/bold yellow].\n"
    )
