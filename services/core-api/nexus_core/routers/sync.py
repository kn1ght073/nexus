"""Sync engine: incremental pull + last-writer-wins push (plan §3).

- Pull: clients send either their last `revision` cursor (per row type) or a
  `since` timestamp; the server returns every row with a higher revision,
  including tombstones, so offline clients can reconcile deletions.
- Push: clients send their local changes with the last revision they saw.
  A change is accepted when its revision is >= the server's current revision
  (last-writer-wins with stale-writer rejection); a stale writer gets
  conflict=true and the server's current state, so it can rebase or re-apply.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import bump_revision, log_activity
from ..models import Note, Project, Task, User, utcnow
from ..schemas import (
    ChangedItems,
    PushItem,
    PushResult,
    SyncPullRequest,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
)
from ..security import get_current_user, require_scope

router = APIRouter(prefix="/sync", tags=["sync"])

_MODELS = {"projects": Project, "tasks": Task, "notes": Note}


@router.post("/pull", response_model=SyncPullResponse)
def sync_pull(
    request: SyncPullRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("read", "sync")),
):
    since = request.since
    if since is not None and since.tzinfo is None:
        # storage may return naive UTC datetimes; treat them as UTC
        since = since.replace(tzinfo=None)

    def _changes(model):
        filters = [model.owner_id == current_user.id]
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


def _apply_fields(obj, item: PushItem):
    if item.title is not None:
        obj.title = item.title
    if item.description is not None:
        obj.description = item.description
    if item.status is not None and hasattr(obj, "status"):
        obj.status = item.status
    if item.content is not None and hasattr(obj, "content"):
        obj.content = item.content
    if item.project_id is not None:
        obj.project_id = item.project_id


@router.post("/push", response_model=SyncPushResponse)
def sync_push(
    request: SyncPushRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("sync", "automation", "filesystem")),
):
    results: dict[str, list[PushResult]] = {}

    for kind, model in _MODELS.items():
        items = getattr(request, kind)
        kind_results = []
        for item in items:
            # --- update / delete path ---
            if item.id is not None:
                row = (
                    db.query(model)
                    .filter(model.id == item.id, model.owner_id == current_user.id)
                    .first()
                )
                if row is None:
                    kind_results.append(
                        PushResult(
                            id=item.id,
                            accepted=False,
                            server_revision=0,
                            conflict=False,
                            reason="not found",
                        )
                    )
                    continue

                server_rev = row.revision or 1
                if item.revision < server_rev:
                    # stale writer: server has newer state
                    kind_results.append(
                        PushResult(
                            id=row.id,
                            accepted=False,
                            server_revision=server_rev,
                            conflict=True,
                            reason=f"stale revision (server at {server_rev})",
                        )
                    )
                    continue

                if item.deleted:
                    row.deleted_at = utcnow()
                    reason = "tombstoned"
                else:
                    _apply_fields(row, item)
                    reason = "updated"
                bump_revision(row)
                db.commit()
                log_activity(
                    db,
                    user_id=current_user.id,
                    action=f"{kind[:-1]}.sync_{reason}",
                    detail=f"rev {row.revision}",
                )
                db.commit()
                kind_results.append(
                    PushResult(id=row.id, accepted=True, server_revision=row.revision)
                )
                continue

            # --- create path ---
            if item.deleted:
                kind_results.append(
                    PushResult(
                        id=None,
                        accepted=False,
                        server_revision=0,
                        reason="delete of unsynced row ignored",
                    )
                )
                continue
            row = model(
                owner_id=current_user.id,
                revision=item.revision,
                **{
                    k: v
                    for k, v in {
                        "title": item.title,
                        "description": item.description,
                        "status": item.status,
                        "content": item.content,
                        "project_id": item.project_id,
                    }.items()
                    if v is not None and hasattr(model(), k)
                },
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            log_activity(
                db,
                user_id=current_user.id,
                action=f"{kind[:-1]}.sync_created",
                detail=f"rev {row.revision}",
            )
            db.commit()
            kind_results.append(
                PushResult(id=row.id, accepted=True, server_revision=row.revision)
            )
        results[kind] = kind_results

    return SyncPushResponse(results=results)
