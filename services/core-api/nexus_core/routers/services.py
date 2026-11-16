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
"""
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

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


def _install_llm(model_size: str) -> list[str]:
    """Ollama is a native app; return the manual steps (driven by the UI)."""
    return [
        "Ollama is a native application, not a pip package.",
        "1. Download from https://ollama.com/download (macOS/Windows/Linux)",
        f"2. Run: ollama pull {model_size}",
        "3. The node auto-detects it at 127.0.0.1:11434 on next boot",
    ]


_INSTALLERS = {"stt": _install_stt, "llm": _install_llm}
_MODEL_SIZES = {"stt": {"base", "small"}, "llm": {"llama3.2", "qwen2.5:3b"}}


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
    """Queue an install job (STT via pip; LLM returns manual steps)."""
    if request.service not in _INSTALLERS:
        raise HTTPException(status_code=400, detail=f"Unknown service '{request.service}'. Available: stt, llm.")
    if request.model and request.model not in _MODEL_SIZES.get(request.service, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{request.model}'. Valid: {sorted(_MODEL_SIZES[request.service])}",
        )
    job_id = next(_next_job)
    job = {
        "id": job_id,
        "service": request.service,
        "model": request.model or ("base" if request.service == "stt" else "llama3.2"),
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
