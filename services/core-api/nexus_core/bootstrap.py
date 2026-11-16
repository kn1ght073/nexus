"""One-time environment bootstrap: the app sets itself up.

User request: "all pip installations, uv, and other setup steps are
performed inside the app" — nobody should hand-type `pip install -r
requirements.txt` or manage venvs/uv manually. This module is the
engine behind:

  - `nexus bootstrap` (CLI)
  - `POST /api/services/install` with service "core" (the API itself)
  - the desktop app's "first-run setup" screen

Design constraints that shaped it:
- NO hard dependency on uv: uv is ~10x faster and preferred when
  present, but plain `python -m venv` + pip works everywhere. The
  resolver picks uv only when it is genuinely on PATH and runnable.
- Everything runs as the logged-in user (no elevation, no system
  Python). The venv lives in a predictable, per-user location.
- Deterministic + testable: `plan_bootstrap()` computes the exact
  command list WITHOUT running anything, so the app can show "here is
  what will run" first and tests can assert the plan; `run_bootstrap()`
  then executes it with live output.
- Mirrors: users on slow/blocked PyPI links (a common reason a manual
  install fails) can set a mirror; we validate the URL shape and pass
  it with --index-url/--extra-index-url semantics preserved.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# Well-known mirrors for the QoL picker (validated URLs, nothing exotic).
PIP_MIRRORS: dict[str, str] = {
    "default": "https://pypi.org/simple",
    "tuna": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "aliyun": "https://mirrors.aliyun.com/pypi/simple",
    "ustc": "https://mirrors.ustc.edu.cn/pypi/simple",
    "sjtu": "https://mirror.sjtu.edu.cn/pypi/web/simple",
}

# Where the managed environment lives (per-user, predictable).
DEFAULT_VENV_DIR = Path.home() / ".nexus-venv"


@dataclass
class BootstrapPlan:
    """Everything `run_bootstrap` will do, computed up front and inspectable."""

    venv_dir: Path
    python_bin: str                       # venv python used for installs
    use_uv: bool                          # uv available and healthy?
    uv_path: Optional[str]                # resolved uv executable
    requirements: list[str]               # requirement specs to install
    index_url: Optional[str]              # mirror, if selected
    commands: list[list[str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def describe(self) -> str:
        head = (
            f"venv: {self.venv_dir}\n"
            f"installer: {'uv' if self.use_uv else 'pip'}"
            + (f" ({self.uv_path})" if self.uv_path else "")
            + (f"\nindex: {self.index_url}" if self.index_url else "")
        )
        reqs = "\n".join(f"  - {r}" for r in self.requirements) or "  (nothing to install)"
        cmds = "\n".join("  $ " + " ".join(c) for c in self.commands)
        extra = "\n".join(f"  ! {n}" for n in self.notes)
        return "\n".join(x for x in (head, reqs, cmds, extra) if x)


def _which_uv() -> Optional[str]:
    """Return an absolute uv path only if it exists AND runs."""
    uv = shutil.which("uv")
    if uv is None:
        return None
    try:
        probe = subprocess.run([uv, "--version"], capture_output=True, text=True, timeout=10)
        if probe.returncode == 0:
            return uv
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def validate_mirror(url: str) -> bool:
    """Accept only http(s) mirror URLs — never file:// or garbage."""
    return url.startswith("https://") or url.startswith("http://")


def resolve_mirror(name_or_url: Optional[str]) -> Optional[str]:
    """Map a mirror picker name (or raw URL) to an index URL."""
    if not name_or_url or name_or_url == "default":
        return None
    if name_or_url in PIP_MIRRORS:
        return PIP_MIRRORS[name_or_url]
    if validate_mirror(name_or_url):
        return name_or_url
    raise ValueError(f"Unknown mirror '{name_or_url}'. Known: {', '.join(PIP_MIRRORS)} (or pass a https:// URL)")


def plan_bootstrap(
    requirements: Optional[list[str]] = None,
    venv_dir: Optional[Path] = None,
    mirror: Optional[str] = None,
    prefer_uv: bool = True,
) -> BootstrapPlan:
    """Compute the full bootstrap plan without running anything.

    requirements default to the core-api pins + the CLI's own pins —
    i.e. "set up the whole NEXUS stack in this venv".
    """
    if requirements is None:
        requirements = [
            "fastapi==0.128.0",
            "uvicorn[standard]==0.44.0",
            "sqlalchemy==2.1.8",
            "pydantic==2.12.5",
            "pydantic-settings==2.13.1",
            "email-validator==2.3.0",
            "argon2-cffi==25.1.0",
            "PyJWT==2.12.1",
            "websockets==16.0",
            "psycopg2-binary==2.9.10",
            "typer==0.23.1",
            "rich==14.3.3",
            "requests==2.32.5",
            "textual==8.2.8",
        ]

    venv_dir = venv_dir or DEFAULT_VENV_DIR
    index_url = resolve_mirror(mirror)
    uv_path = _which_uv() if prefer_uv else None
    use_uv = uv_path is not None

    suffix = ".exe" if os.name == "nt" else ""
    venv_python = venv_dir / ("Scripts" if os.name == "nt" else "bin") / f"python{suffix}"

    commands: list[list[str]] = []
    notes: list[str] = []

    if not venv_dir.exists():
        if use_uv:
            commands.append([uv_path, "venv", str(venv_dir), "--python", sys.version.split()[0]])
            notes.append("uv creates the venv in milliseconds; falls back to stdlib venv without uv.")
        else:
            commands.append([sys.executable, "-m", "venv", str(venv_dir)])
    else:
        notes.append(f"venv already exists at {venv_dir} — reusing it.")

    install: list[str]
    if use_uv:
        install = [uv_path, "pip", "install", "--python", str(venv_python)]
        if index_url:
            install += ["--index-url", index_url]
    else:
        install = [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"]
        commands.append(install)
        install = [str(venv_python), "-m", "pip", "install"]
        if index_url:
            install += ["--index-url", index_url]
    install += requirements
    commands.append(install)

    return BootstrapPlan(
        venv_dir=venv_dir,
        python_bin=str(venv_python),
        use_uv=use_uv,
        uv_path=uv_path,
        requirements=requirements,
        index_url=index_url,
        commands=commands,
        notes=notes,
    )


def run_bootstrap(
    plan: BootstrapPlan,
    echo: Optional[Callable[[str], None]] = None,
) -> bool:
    """Execute a plan; `echo` receives live progress lines.

    Returns True on success. Any failure returns False with the failing
    command + tail of its output already echoed — the caller (app/CLI)
    just surfaces it to the user with the plan description.
    """
    def say(line: str) -> None:
        if echo:
            echo(line)

    say(f"[bootstrap] {plan.describe()}")

    # 1. create the venv (uv or stdlib) if needed
    if not plan.venv_dir.exists():
        if plan.use_uv:
            create = [plan.uv_path, "venv", str(plan.venv_dir), "--python", sys.version.split()[0]]
        else:
            create = [sys.executable, "-m", "venv", str(plan.venv_dir)]
        say(f"[bootstrap] creating venv at {plan.venv_dir}")
        if not _run(create, say):
            return False
    else:
        say(f"[bootstrap] reusing venv at {plan.venv_dir}")

    # 2. pip self-upgrade (pip path only)
    if not plan.use_uv:
        say("[bootstrap] upgrading pip inside the venv")
        _run([plan.python_bin, "-m", "pip", "install", "--upgrade", "pip"], say)

    # 3. install the requirements (mirror already baked into the plan)
    say("[bootstrap] installing requirements (this is the slow step)")
    if not _install_requirements(plan, say):
        return False

    say("[bootstrap] done — environment ready")
    return True


def _install_requirements(plan: BootstrapPlan, say: Callable[[str], None]) -> bool:
    if plan.use_uv:
        cmd = [plan.uv_path, "pip", "install", "--python", plan.python_bin]
        if plan.index_url:
            cmd += ["--index-url", plan.index_url]
    else:
        cmd = [plan.python_bin, "-m", "pip", "install"]
        if plan.index_url:
            cmd += ["--index-url", plan.index_url]
    cmd += plan.requirements
    return _run(cmd, say)


def _run(cmd: list[str], say: Callable[[str], None], timeout: int = 900) -> bool:
    """Run one command, streaming the last lines of output on failure."""
    say(f"[bootstrap] $ {' '.join(str(c) for c in cmd)}")
    try:
        proc = subprocess.run(
            [str(c) for c in cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        say(f"[bootstrap] FAILED to start: {exc}")
        return False
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-15:]
        for line in tail:
            say(f"[bootstrap]   {line}")
        say("[bootstrap] FAILED — see output above")
        return False
    return True


def write_uv_config(mirror: Optional[str] = None) -> Optional[Path]:
    """Persist the chosen mirror for future uv runs (~/.config/uv/uv.toml).

    uv does not read pip-style env vars the same way; writing its config
    once keeps `uv` behaves identically to the pip fallback.
    """
    index_url = resolve_mirror(mirror)
    if not index_url:
        return None
    cfg_dir = Path.home() / ".config" / "uv"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = cfg_dir / "uv.toml"
    cfg.write_text(
        f'[[index]]\nurl = "{index_url}"\ndefault = true\n',
        encoding="utf-8",
    )
    return cfg
