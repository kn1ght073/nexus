"""Shared query helpers: ownership filtering and activity logging.

Every router goes through these so no query can ever return another
user's rows (fixes error C4: GET /tasks and /notes were unfiltered).
"""
from sqlalchemy.orm import Session

from .events import DomainEvent, publish
from .models import Activity, User


def log_activity(db: Session, user_id: int, action: str, detail: str = "", device_id: int | None = None) -> None:
    db.add(Activity(user_id=user_id, device_id=device_id, action=action, detail=detail))


def publish_event(event_type: str, user_id: int, data: dict | None = None) -> None:
    publish(DomainEvent(type=event_type, user_id=user_id, data=data or {}))


def bump_revision(obj) -> None:
    """Bump the sync revision on a mutable row (Project/Task/Note).

    Call right before commit on every mutation path (create starts at 1);
    the revision lets /sync/push detect stale writers (last-writer-wins).
    """
    current = getattr(obj, "revision", None)
    obj.revision = (current or 0) + 1


def owned_project_or_404(db: Session, user: User, project_id: int):
    from fastapi import HTTPException

    from .models import Project

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user.id, Project.deleted_at.is_(None))
        .first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
