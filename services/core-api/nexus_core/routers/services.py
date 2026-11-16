"""Node services: install/inspect optional local AI services (STT, LLM).

The desktop app asks "which optional services does this node have?" and,
when the user wants voice capture, prompts to install. Installation runs
ON THE NODE (this machine) as the logged-in user; the API just drives it.

Everything is deliberately conservative:
- Detection is passive (import probe / port probe) — no downloads.
- Install endpoints require the "admin" or "devices" scope (the node
  owner's interactive token or a paired device with those capabilities).
- pip install output is streamed to a job row, not to the response, so a
  desktop UI can show progress without blocking.
- STT model size is chosen by the user (base ~150 MB for voice notes,
  small ~460 MB for accuracy); the download happens on first use through
  faster-whisper itself.

`GET /packages` additionally publishes the whole setup surface as a
machine-readable plan (links, sizes, mirrors, uv/pip availability) so
first-run screens in the app can render "what gets installed, from
where, how big" without hardcoding anything. `POST /install` with
service "bootstrap" runs the full environment self-setup (venv + pinned
dependencies, uv when available) via nexus_core/bootstrap.py.
"""
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..bootstrap import PIP_MIRRORS, plan_bootstrap
from ..database import get_db
from ..deps import log_activity
from ..models import User
from ..schemas import ServiceInstallRequest, ServiceInstallStatus, ServiceStatusResponse
from ..security import get_current_user, require_scope
from ..settings import get_settings

router = APIRouter(prefix="/services", tags=["services"])
settings = get_settings()

# In-memory job table (single worker); moved to the DB when jobs outlive
# the process (they do not — installs finish in seconds/minutes).
_jobs: dict[int, dict] = {}
_next_job = iter(range(1, 10**9))

# What the app can install, as data (docs/deploy/online-access.md Part 4
# renders this table for humans; /packages renders it for apps).
PACKAGES: dict[str, dict] = {
    "stt": {
        "label": "Speech-to-text (voice notes)",
        "module": "faster-whisper",
        "size_first_use": "~150 MB (base model)",
        "docs": "https://github.com/SYSTRAN/faster-whisper",
        "install": "pip (driven by the app)",
        "prompt": "Install transcription? The base model (~150 MB) downloads on first use.",
    },
    "llm": {
        "label": "Local LLM (intent extraction)",
        "module": "ollama",
        "size_first_use": "~2 GB (llama3.2 3B)",
        "docs": "https://ollama.com/download",
        "install": "native app",
        "prompt": "Install Ollama from ollama.com, then pull llama3.2 — the node auto-detects it.",
    },
}


def detect_local_services() -> dict:
    """Probe this machine for installable services (no network, no side effects)."""
    services: dict[str, str] = {}
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


def _install_stt(model_size: str) -> list[str]:
    """pip-install faster-whisper. Model weights download on first use."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "faster-whisper"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:] or "pip install failed")
    return [
        "faster-whisper installed",
        f"model '{model_size}' downloads on first transcription "
        f"(base ≈ 150 MB, small ≈ 460 MB) — no pre-download needed",
    ]


def _install_bootstrap(model_size: str) -> list[str]:
    """Full environment self-setup: venv + pinned deps, uv when available.

    This is the engine behind "all pip/uv/setup steps happen inside the
    app": the first-run screen calls POST /install {service: bootstrap}
    and the node prepares its own runtime (nexus_core/bootstrap.py).
    """
    from ..bootstrap import run_bootstrap

    lines: list[str] = []
    plan = plan_bootstrap(mirror=(model_size or None) if model_size in PIP_MIRRORS else None)
    lines.append(plan.describe())
    ok = run_bootstrap(plan, echo=lines.append)
    if not ok:
        raise RuntimeError("bootstrap failed — see steps above")
    lines.append(f"run the node with: {plan.python_bin} -m uvicorn nexus_core.main:app")
    return lines


def _install_llm(model_size: str) -> list[str]:
    """Ollama is a native app; return the manual steps (driven by the UI)."""
    return [
        "Ollama is a native application, not a pip package.",
        "1. Download from https://ollama.com/download (macOS/Windows/Linux)",
        f"2. Run: ollama pull {model_size}",
        "3. The node auto-detects it at 127.0.0.1:11434 on next boot",
    ]


_INSTALLERS = {"stt": _install_stt, "llm": _install_llm, "bootstrap": _install_bootstrap}
_MODEL_SIZES = {"stt": {"base", "small"}, "llm": {"llama3.2", "qwen2.5:3b"}}
# bootstrap reuses the mirror names as its "model" values
MODEL_NAMES_ALL = set(PIP_MIRRORS) | {"base", "small", "llama3.2", "qwen2.5:3b"}


@router.get("/packages")
def packages(
    mirror: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """Machine-readable setup plan for first-run app screens.

    Includes: what each service is, sizes, official links, whether uv is
    available on this machine, the mirror list (QoL for slow PyPI
    links), and the exact environment plan the bootstrap would run.
    """
    try:
        plan = plan_bootstrap(mirror=mirror)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "services": PACKAGES,
        "environment": {
            "uv_available": plan.use_uv,
            "venv_dir": str(plan.venv_dir),
            "python": plan.python_bin,
            "index_url": plan.index_url or PIP_MIRRORS["default"],
            "requirements": plan.requirements,
            "commands": [" ".join(str(c) for c in cmd) for cmd in plan.commands],
            "notes": plan.notes,
        },
        "mirrors": PIP_MIRRORS,
        "docs": {
            "uv": "https://docs.astral.sh/uv/",
            "pip": "https://pip.pypa.io/en/stable/",
            "python": "https://www.python.org/downloads/",
            "setup_guide": "docs/deploy/online-access.md#part-4--everything-installs-from-inside-the-app-no-terminal-required",
        },
    }


@router.get("/status", response_model=ServiceStatusResponse)
def service_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Which optional services this node has installed right now."""
    installed = detect_local_services()
    return ServiceStatusResponse(
        installed=installed,
        available={
            "stt": "faster-whisper (speech-to-text for the Universal Inbox)",
            "llm": "Ollama (local intent extraction)",
        },
    )


@router.post("/install", response_model=ServiceInstallStatus, status_code=202)
def install_service(
    request: ServiceInstallRequest,
    background: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("admin", "devices")),
):
    """Queue an install job (STT via pip; LLM returns manual steps; bootstrap
    prepares the whole environment — venv + pinned deps, uv when present)."""
    if request.service not in _INSTALLERS:
        raise HTTPException(status_code=400, detail=f"Unknown service '{request.service}'. Available: stt, llm, bootstrap.")
    if request.service == "bootstrap":
        # model field re-used as the mirror name for bootstrap
        if request.model and request.model not in PIP_MIRRORS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown mirror '{request.model}'. Valid: {', '.join(PIP_MIRRORS)} (or omit for default).",
            )
    elif request.model and request.model not in _MODEL_SIZES.get(request.service, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{request.model}'. Valid: {sorted(_MODEL_SIZES[request.service])}",
        )
    job_id = next(_next_job)
    default_model = "base" if request.service == "stt" else ("default" if request.service == "bootstrap" else "llama3.2")
    job = {
        "id": job_id,
        "service": request.service,
        "model": request.model or default_model,
        "status": "running",
        "steps": [],
        "error": None,
    }
    _jobs[job_id] = job

    def _run():
        try:
            job["steps"] = _INSTALLERS[request.service](job["model"])
            job["status"] = "completed"
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)

    background.add_task(_run)
    log_activity(db, user_id=current_user.id, action="services.install", detail=f"{request.service} job #{job_id}")
    db.commit()
    return ServiceInstallStatus(**job)


@router.get("/install/{job_id}", response_model=ServiceInstallStatus)
def install_status(job_id: int, current_user: User = Depends(get_current_user)):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Install job not found")
    return ServiceInstallStatus(**job)
