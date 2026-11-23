"""GitHub OAuth linking and highlights commands."""

import time
import webbrowser
from typing import Optional

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from ..client import get_client
from ..errors import ExitCode, NexusError
from ..ui import console, create_table, is_json_mode, output_json, print_error, print_info, print_success, render_key_value, set_json_mode, status_spinner

github_app = typer.Typer(help="Link GitHub account and view activity highlights")


@github_app.command("status")
def github_status(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Check GitHub account linking status."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    try:
        resp = client.get("/api/github/status")
        body = resp.json()
        if is_json_mode():
            output_json(body)
            return

        if not body.get("linked"):
            console.print(
                Panel("No GitHub account linked.\nRun [bold cyan]nexus github connect[/bold cyan].", title="GitHub", border_style="yellow", expand=False)
            )
            return

        p = body.get("profile", {})
        console.print(
            Panel(
                f"[bold cyan]{p.get('login')}[/bold cyan] (id {p.get('github_id')})\nlinked {(p.get('linked_at') or '')[:10]} · scopes: {p.get('scopes')}",
                title="[bold green]GitHub linked[/bold green]",
                border_style="green",
                expand=False,
            )
        )
    except NexusError as e:
        console.print(Panel(str(e.message), title="[bold red]Error[/bold red]", border_style="red", expand=False))
        raise typer.Exit(e.exit_code)


@github_app.command("connect")
def github_connect(scopes: Optional[str] = typer.Option(None, "--scopes", help="Override OAuth scopes (default: read:user)")):
    """Link GitHub account using Device Flow (works headless & over SSH)."""
    client = get_client()
    try:
        with status_spinner("Requesting GitHub device authorization…"):
            resp = client.post("/api/github/device/start", json={"scopes": scopes} if scopes else {})
        start = resp.json()

        verification_uri = start["verification_uri"]
        user_code = start["user_code"]
        expires_in = start.get("expires_in", 900)
        interval = max(int(start.get("interval", 5)), 1)
        device_code = start["device_code"]

        if is_json_mode():
            output_json(start)
        else:
            console.print(
                Panel(
                    f"Open [bold cyan]{verification_uri}[/bold cyan]\n"
                    f"and enter code: [bold green]{user_code}[/bold green]\n"
                    f"[dim]valid for {expires_in // 60} minutes — this window polls until you approve.[/dim]",
                    title="[bold cyan]Link GitHub[/bold cyan]",
                    border_style="cyan",
                    expand=False,
                )
            )
            try:
                webbrowser.open(verification_uri)
            except Exception:
                pass

        deadline = time.monotonic() + expires_in
        while time.monotonic() < deadline:
            time.sleep(interval)
            try:
                poll_resp = client.post("/api/github/device/poll", json={"device_code": device_code})
                body = poll_resp.json()
                st = body.get("status")

                if st == "linked":
                    p = body.get("profile", {})
                    console.print(
                        Panel(
                            f"GitHub account [bold cyan]{p.get('login')}[/bold cyan] linked (scopes: {p.get('scopes')}).\n"
                            "Try [bold cyan]nexus github highlights[/bold cyan].",
                            title="[bold green]GitHub linked[/bold green]",
                            border_style="green",
                            expand=False,
                        )
                    )
                    return
                elif st == "slow_down":
                    interval += 5
                elif st == "pending":
                    continue
                else:
                    console.print(Panel(f"[bold red]{st}[/bold red]\n[dim]{body.get('detail', '')}[/dim]", title="[bold red]Link failed[/bold red]", border_style="red", expand=False))
                    raise typer.Exit(ExitCode.FAILURE)
            except NexusError as ex:
                console.print(Panel(ex.message, title="[bold red]Poll failed[/bold red]", border_style="red", expand=False))
                raise typer.Exit(ex.exit_code)

        console.print(Panel("Timed out waiting for approval — run [bold cyan]nexus github connect[/bold cyan] again.", title="[bold yellow]Expired[/bold yellow]", border_style="yellow", expand=False))
        raise typer.Exit(ExitCode.TIMEOUT)
    except NexusError as e:
        console.print(Panel(e.message, title="[bold red]GitHub link failed[/bold red]", border_style="red", expand=False))
        raise typer.Exit(e.exit_code)


@github_app.command("highlights")
def github_highlights(
    refresh: bool = typer.Option(False, "--refresh", help="Bypass 5-minute cache and fetch fresh"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Display GitHub profile highlights, starred repos, and recent commits."""
    if json_output:
        set_json_mode(True)
    client = get_client()
    params = {"refresh": "true"} if refresh else {}
    try:
        with status_spinner("Fetching GitHub highlights…"):
            resp = client.get("/api/github/highlights", params=params)
        data = resp.json()
        if is_json_mode():
            output_json(data)
            return

        p = data.get("profile", {})
        repos = data.get("repos", [])
        events = data.get("events", [])
        cached_note = " [dim](cached)[/dim]" if data.get("cached") else ""

        console.print(
            Panel(
                f"[bold]{data.get('login')}[/bold] — {p.get('name') or ''}\n"
                + (f"[dim]{p.get('bio') or ''}[/dim]\n" if p.get("bio") else "")
                + f"repos {p.get('public_repos')} · followers {p.get('followers')} · following {p.get('following')}"
                + (f" · {p.get('company')}" if p.get("company") else "")
                + (f" · {p.get('location')}" if p.get("location") else ""),
                title=f"GitHub highlights{cached_note}",
                border_style="cyan",
                expand=False,
            )
        )

        if repos:
            table = Table(title="Recent repositories", box=box.ROUNDED, header_style="bold cyan")
            table.add_column("Repo", style="cyan")
            table.add_column("★", justify="right")
            table.add_column("Lang")
            table.add_column("Last push")
            for repo in repos:
                table.add_row(
                    repo["name"] or "?",
                    str(repo.get("stars", 0)),
                    repo.get("language") or "-",
                    (repo.get("pushed_at") or "")[:10] or "-",
                )
            console.print(table)

        for e in events:
            console.print(f"  • [dim]{(e.get('created_at') or '')[:10]}[/dim] {e.get('detail')}")
    except NexusError as e:
        console.print(Panel(str(e.message), title="[bold red]Error[/bold red]", border_style="red", expand=False))
        raise typer.Exit(e.exit_code)


@github_app.command("unlink")
def github_unlink():
    """Unlink GitHub account and revoke token."""
    client = get_client()
    try:
        with status_spinner("Unlinking GitHub account…"):
            client.delete("/api/github/link")
        console.print(Panel("GitHub account unlinked and token revoked.", title="[bold green]Unlinked[/bold green]", border_style="green", expand=False))
    except NexusError as e:
        console.print(Panel(str(e.message), title="[bold red]Error[/bold red]", border_style="red", expand=False))
        raise typer.Exit(e.exit_code)
