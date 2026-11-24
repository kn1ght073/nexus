"""Projects: create, list (with filters), retrieve, update status, soft-delete."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import bump_revision, log_activity, owned_project_or_404, publish_event
from ..database import get_db
from ..models import Project, User
from ..schemas import ProjectCreate, ProjectOut, StatusUpdate
from ..security import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import datetime
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=5)
    existing = (
        db.query(Project)
        .filter(
            Project.owner_id == current_user.id,
            Project.title == project_in.title,
            Project.created_at >= cutoff,
            Project.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        return existing

    project = Project(**project_in.model_dump(), owner_id=current_user.id)
    db.add(project)
    bump_revision(project)  # sync: revision +1
    db.commit()
    db.refresh(project)
    log_activity(db, user_id=current_user.id, action="project.created", detail=project.title)
    publish_event("PROJECT_CREATED", current_user.id, {"project_id": project.id, "title": project.title})
    db.commit()
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Project).filter(Project.owner_id == current_user.id, Project.deleted_at.is_(None))
    if status_filter:
        query = query.filter(Project.status == status_filter)
    return query.order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return owned_project_or_404(db, current_user, project_id)


@router.patch("/{project_id}/status", response_model=ProjectOut)
def update_project_status(
    project_id: int,
    status_update: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = owned_project_or_404(db, current_user, project_id)
    project.status = status_update.status
    bump_revision(project)  # sync: revision +1
    db.commit()
    db.refresh(project)
    log_activity(db, user_id=current_user.id, action="project.status_changed", detail=f"{project.title} -> {project.status}")
    publish_event("PROJECT_UPDATED", current_user.id, {"project_id": project.id, "status": project.status})
    db.commit()
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = owned_project_or_404(db, current_user, project_id)
    from ..models import utcnow

    project.deleted_at = utcnow()  # tombstone, not row deletion (sync §3)
    bump_revision(project)  # sync: revision +1
    db.commit()
    log_activity(db, user_id=current_user.id, action="project.deleted", detail=project.title)
    publish_event("PROJECT_DELETED", current_user.id, {"project_id": project.id})
    db.commit()
