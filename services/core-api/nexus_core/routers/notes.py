"""Notes: create, list, retrieve, delete (soft). Same ownership discipline as tasks."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..deps import log_activity, owned_project_or_404, publish_event
from ..database import get_db
from ..models import Note, User
from ..schemas import NoteCreate, NoteOut
from ..security import get_current_user

router = APIRouter(prefix="/notes", tags=["notes"])


def _owned_note_or_404(db: Session, user: User, note_id: int) -> Note:
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.owner_id == user.id, Note.deleted_at.is_(None))
        .first()
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("", response_model=NoteOut, status_code=201)
def create_note(
    note_in: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if note_in.project_id is not None:
        owned_project_or_404(db, current_user, note_in.project_id)
    note = Note(**note_in.model_dump(), owner_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    log_activity(db, user_id=current_user.id, action="note.created", detail=note.title)
    publish_event("NOTE_CREATED", current_user.id, {"note_id": note.id, "title": note.title})
    db.commit()
    return note


@router.get("", response_model=list[NoteOut])
def list_notes(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ownership-filtered (fixes C4: previously db.query(Note).all())."""
    filters = [Note.owner_id == current_user.id, Note.deleted_at.is_(None)]
    if project_id is not None:
        filters.append(Note.project_id == project_id)
    return db.query(Note).filter(and_(*filters)).order_by(Note.created_at.desc()).all()


@router.get("/{note_id}", response_model=NoteOut)
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _owned_note_or_404(db, current_user, note_id)


@router.delete("/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _owned_note_or_404(db, current_user, note_id)
    from ..models import utcnow

    note.deleted_at = utcnow()
    db.commit()
    log_activity(db, user_id=current_user.id, action="note.deleted", detail=note.title)
    publish_event("NOTE_DELETED", current_user.id, {"note_id": note.id})
    db.commit()
