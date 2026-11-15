"""Sync pull: incremental change feed (foundation for the plan's §3 sync engine).

Clients send the timestamp of their last successful pull; the server returns
every project/task/note row updated since then, including tombstones
(deleted_at set) so clients can reconcile deletions offline-first.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Note, Project, Task, User
from ..schemas import ChangedItems, SyncPullRequest, SyncPullResponse
from ..models import utcnow
from ..security import get_current_user

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/pull", response_model=SyncPullResponse)
def sync_pull(
    request: SyncPullRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = request.since
    if since is not None and since.tzinfo is None:
        # storage may return naive UTC datetimes; treat them as UTC
        since = since.replace(tzinfo=None)

    def _changes(model, extra_filters=None):
        filters = [model.owner_id == current_user.id]
        if extra_filters:
            filters.extend(extra_filters)
        if since is None:
            # first pull: everything not tombstoned
            filters.append(model.deleted_at.is_(None))
            return db.query(model).filter(and_(*filters)).all()
        filters.append(model.updated_at >= since)
        return db.query(model).filter(and_(*filters)).all()

    return SyncPullResponse(
        server_time=utcnow(),
        changes=ChangedItems(
            projects=_changes(Project),
            tasks=_changes(Task),
            notes=_changes(Note),
        ),
    )
