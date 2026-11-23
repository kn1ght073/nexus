"""Terminal presentation, styling, and formatting engine for NEXUS CLI."""

import json as _json
import os
import sys
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Respect NO_COLOR standard (https://no-color.org)
NO_COLOR = bool(os.environ.get("NO_COLOR"))

# Standard consoles: stdout for clean output, stderr for logs/spinners/diagnostics
console = Console(no_color=NO_COLOR, highlight=False)
err_console = Console(stderr=True, no_color=NO_COLOR, highlight=False)

# Machine-readable output toggle
JSON_MODE = {"enabled": False}


def is_json_mode() -> bool:
    return JSON_MODE["enabled"]


def set_json_mode(enabled: bool) -> None:
    JSON_MODE["enabled"] = enabled


def output_json(data: Any) -> None:
    """Print valid, machine-readable JSON to stdout."""
    if JSON_MODE["enabled"]:
        print(_json.dumps(data, indent=2, default=str))


def print_error(message: str, title: str = "ERROR", hint: Optional[str] = None, details: Optional[str] = None) -> None:
    """Render a high-visibility, formatted error panel to stderr."""
    if is_json_mode():
        err_data = {"error": True, "title": title, "message": message}
        if hint:
            err_data["hint"] = hint
        if details:
            err_data["details"] = details
        err_console.print(_json.dumps(err_data, indent=2))
        return

    body = f"[bold red]{message}[/bold red]"
    if details:
        body += f"\n[dim]{details}[/dim]"
    if hint:
        body += f"\n\n[cyan]Tip:[/cyan] [dim]{hint}[/dim]"

    err_console.print(
        Panel(
            body,
            title=f"[bold red]{title}[/bold red]",
            border_style="red",
            box=box.ROUNDED,
            expand=False,
        )
    )


def print_success(message: str, title: str = "SUCCESS", details: Optional[str] = None) -> None:
    if is_json_mode():
        return
    body = f"[bold green]{message}[/bold green]"
    if details:
        body += f"\n[dim]{details}[/dim]"
    console.print(
        Panel(
            body,
            title=f"[bold green]{title}[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            expand=False,
        )
    )


def print_warning(message: str, title: str = "WARNING", hint: Optional[str] = None) -> None:
    if is_json_mode():
        return
    body = f"[bold yellow]{message}[/bold yellow]"
    if hint:
        body += f"\n[dim]{hint}[/dim]"
    console.print(
        Panel(
            body,
            title=f"[bold yellow]{title}[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            expand=False,
        )
    )


def print_info(message: str, title: str = "INFO", details: Optional[str] = None) -> None:
    if is_json_mode():
        return
    body = message
    if details:
        body += f"\n[dim]{details}[/dim]"
    console.print(
        Panel(
            body,
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            expand=False,
        )
    )


def create_table(title: str, columns: List[Dict[str, Any]], box_style: Any = box.ROUNDED) -> Table:
    """Create a standardized table with consistent brand styling."""
    t = Table(
        title=f"[bold cyan]{title}[/bold cyan]" if title else None,
        box=box_style,
        header_style="bold cyan",
        show_header=True,
    )
    for col in columns:
        t.add_column(
            col.get("name", ""),
            justify=col.get("justify", "left"),
            style=col.get("style", None),
            width=col.get("width", None),
            no_wrap=col.get("no_wrap", False),
        )
    return t


def render_table(rows: List[List[Any]], headers: List[str], title: Optional[str] = None) -> None:
    """Render a formatted table directly to console."""
    if is_json_mode():
        return
    t = Table(
        title=f"[bold cyan]{title}[/bold cyan]" if title else None,
        box=box.ROUNDED,
        header_style="bold cyan",
        show_header=True,
    )
    for h in headers:
        t.add_column(h)
    for row in rows:
        t.add_row(*[str(cell) for cell in row])
    console.print(t)


def render_key_value(pairs: Dict[str, Any], title: Optional[str] = None) -> None:
    """Render a clean key-value block aligned with borders."""
    if is_json_mode():
        output_json(pairs)
        return
    lines = []
    max_k = max(len(k) for k in pairs.keys()) if pairs else 0
    for k, v in pairs.items():
        v_str = "[dim]None[/dim]" if v is None else str(v)
        lines.append(f"  [bold cyan]{k.ljust(max_k)}[/bold cyan] : {v_str}")
    content = "\n".join(lines) if lines else "[dim]No properties[/dim]"
    if title:
        console.print(Panel(content, title=f"[bold cyan]{title}[/bold cyan]", border_style="cyan", expand=False))
    else:
        console.print(content)


@contextmanager
def status_spinner(message: str):
    """Execution progress indicator that respects JSON mode and TTY constraints."""
    if is_json_mode() or not sys.stderr.isatty():
        yield
        return
    with err_console.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots"):
        yield
