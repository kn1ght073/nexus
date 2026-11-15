"""Tasks: create, list (today/filter), update status, complete, soft-delete."""
from datetime import datetime, time, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..deps import log_activity, owned_project_or_404, publish_event
from ..database import get_db
from ..models import Task, User
from ..schemas import StatusUpdate, TaskCreate, TaskOut
from ..security import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _owned_task_or_404(db: Session, user: User, task_id: int) -> Task:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.owner_id == user.id, Task.deleted_at.is_(None))
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskOut, status_code=201)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if task_in.project_id is not None:
        owned_project_or_404(db, current_user, task_in.project_id)
    task = Task(**task_in.model_dump(), owner_id=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    log_activity(db, user_id=current_user.id, action="task.created", detail=task.title)
    publish_event("TASK_CREATED", current_user.id, {"task_id": task.id, "title": task.title, "status": task.status})
    db.commit()
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(
    project_id: int | None = None,
    status_filter: Literal["pending", "in_progress", "completed"] | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ownership-filtered task list (fixes C4: previously db.query(Task).all())."""
    filters = [Task.owner_id == current_user.id, Task.deleted_at.is_(None)]
    if project_id is not None:
        filters.append(Task.project_id == project_id)
    if status_filter is not None:
        filters.append(Task.status == status_filter)
    return db.query(Task).filter(and_(*filters)).order_by(Task.created_at.desc()).all()


@router.get("/today", response_model=list[TaskOut])
def today_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tasks created or completed today (backing `nexus task today`)."""
    start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    return (
        db.query(Task)
        .filter(
            Task.owner_id == current_user.id,
            Task.deleted_at.is_(None),
            Task.created_at >= start,
        )
        .order_by(Task.created_at.desc())
        .all()
    )


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _owned_task_or_404(db, current_user, task_id)


@router.patch("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: int,
    status_update: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _owned_task_or_404(db, current_user, task_id)
    task.status = status_update.status
    db.commit()
    db.refresh(task)
    log_activity(db, user_id=current_user.id, action="task.status_changed", detail=f"{task.title} -> {task.status}")
    publish_event("TASK_UPDATED", current_user.id, {"task_id": task.id, "status": task.status})
    db.commit()
    return task


@router.post("/{task_id}/done", response_model=TaskOut)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convenience endpoint backing `nexus task done <id>`."""
    task = _owned_task_or_404(db, current_user, task_id)
    task.status = "completed"
    db.commit()
    db.refresh(task)
    log_activity(db, user_id=current_user.id, action="task.completed", detail=task.title)
    publish_event("TASK_COMPLETED", current_user.id, {"task_id": task.id, "title": task.title})
    db.commit()
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _owned_task_or_404(db, current_user, task_id)
    from ..models import utcnow

    task.deleted_at = utcnow()  # tombstone for sync
    db.commit()
    log_activity(db, user_id=current_user.id, action="task.deleted", detail=task.title)
    publish_event("TASK_DELETED", current_user.id, {"task_id": task.id})
    db.commit()
