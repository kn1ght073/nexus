"""Universal Inbox: capture-anything endpoint feeding the AI pipeline.

POST /api/inbox accepts text (and, in production, audio blobs saved by the
file layer). Each item becomes a job row; a background task runs
STT (audio only) -> LLM intent extraction -> action engine. Clients get 202
immediately (the plan's flagship flow, §3).
"""
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..deps import log_activity
from ..models import InboxItem, User
from ..security import get_current_user, require_scope
from ..settings import get_settings

router = APIRouter(prefix="/inbox", tags=["inbox"])
settings = get_settings()


@router.post("", status_code=202)
def submit_text(
    text: str = Form(..., min_length=1),
    background: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("capture", "sync", "automation")),
):
    """Text capture: queue the pipeline job and return immediately."""
    item = InboxItem(kind="text", content=text, owner_id=current_user.id, status="pending")
    db.add(item)
    db.commit()
    db.refresh(item)
    log_activity(db, user_id=current_user.id, action="inbox.submitted", detail=f"text #{item.id}")
    db.commit()
    background.add_task(run_pipeline, item.id)
    return JSONResponse({"inbox_item_id": item.id, "status": "accepted"}, status_code=202)


@router.post("/audio", status_code=202)
async def submit_audio(
    audio: UploadFile = File(...),
    background: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("capture", "sync", "automation")),
):
    """Voice capture: persist the blob to the storage root and queue STT."""
    root = Path(settings.storage_roots[0]) / "inbox"
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{current_user.id}_{audio.filename or 'voice'}"
    size = 0
    with target.open("wb") as out:
        while chunk := await audio.read(1024 * 1024):
            size += len(chunk)
            out.write(chunk)
    if size == 0:
        raise HTTPException(status_code=400, detail="empty upload")

    item = InboxItem(kind="audio", content=str(target), owner_id=current_user.id, status="pending")
    db.add(item)
    db.commit()
    db.refresh(item)
    log_activity(db, user_id=current_user.id, action="inbox.submitted", detail=f"audio #{item.id} ({size}B)")
    db.commit()
    background.add_task(run_pipeline, item.id)
    return JSONResponse({"inbox_item_id": item.id, "status": "accepted", "bytes": size}, status_code=202)


@router.get("/{item_id}")
def inbox_status(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = (
        db.query(InboxItem)
        .filter(InboxItem.id == item_id, InboxItem.owner_id == current_user.id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    import json as _json

    try:
        result = _json.loads(item.result) if item.result else None
    except ValueError:
        result = item.result
    return {
        "id": item.id,
        "kind": item.kind,
        "status": item.status,
        "result": result,
        "error": item.error,
        "created_at": item.created_at,
    }


# --- the pipeline ------------------------------------------------------------

def run_pipeline(item_id: int) -> None:
    """STT -> intent -> action engine, on a fresh session; statuses recorded."""
    from ..workers.stt import transcribe
    from ..workers.llm import extract_intent, IntentValidationError
    from ..workers.action_engine import execute_intent, ActionError

    db = SessionLocal()
    try:
        item = db.query(InboxItem).get(item_id)
        if item is None:
            return
        item.status = "processing"
        db.commit()

        try:
            # 1) STT (audio only; text passes through)
            if item.kind == "audio":
                transcript_obj = transcribe(item.content)
                transcript = transcript_obj.text
                item.transcript = transcript
                item.backend = transcript_obj.backend
            else:
                transcript = item.content

            # 2) LLM intent extraction (strict schema validation)
            intent = extract_intent(transcript)

            # 3) Deterministic action engine
            user = db.query(User).get(item.owner_id)
            result = execute_intent(db, user, intent, source=item.kind)
            import json as _json

            item.result = _json.dumps(result)
            item.status = "completed"
        except (IntentValidationError, ActionError) as e:
            item.status = "rejected"
            item.error = str(e)
        except Exception as e:  # worker crash must not lose the item
            item.status = "failed"
            item.error = f"{type(e).__name__}: {e}"
        db.commit()
    finally:
        db.close()
