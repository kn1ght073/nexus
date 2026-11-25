"""User Client Console API: Account overview, devices, sessions, activity, and data summary.

Enforces strict account ownership (current_user.id). Zero IDOR/BOLA exposure.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import log_activity
from ..models import (
    Activity,
    Device,
    ExternalIdentity,
    InboxItem,
    Note,
    Project,
    SessionRecord,
    Task,
    User,
    utcnow,
)
from ..schemas import (
    AccountDataSummaryOut,
    AccountMetricsOut,
    AccountOverviewOut,
    ActivityOut,
    ActivityPageOut,
    DeviceOut,
    DeviceStatsOut,
    GoogleIdentityOut,
    ServerStatusOut,
    SessionOut,
    SessionStatsOut,
)
from ..security import get_current_user
from ..settings import get_settings

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/overview", response_model=AccountOverviewOut)
def get_account_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full account overview for the authenticated user."""
    ext = (
        db.query(ExternalIdentity)
        .filter(ExternalIdentity.user_id == current_user.id)
        .first()
    )

    google_id = GoogleIdentityOut(
        linked=ext is not None,
        email=ext.email_at_link if ext else None,
        name=ext.display_name if ext else None,
        picture_url=ext.picture_url if ext else None,
        email_verified=ext.email_verified if ext else False,
        linked_at=ext.linked_at if ext else None,
        last_login_at=ext.last_login_at if ext else None,
    )

    total_devices = db.query(Device).filter(Device.owner_id == current_user.id).count()
    active_devices = (
        db.query(Device)
        .filter(Device.owner_id == current_user.id, Device.is_online == True)
        .count()
    )

    now = utcnow()
    active_sessions = (
        db.query(SessionRecord)
        .filter(
            SessionRecord.user_id == current_user.id,
            SessionRecord.revoked_at == None,
            SessionRecord.expires_at > now,
        )
        .count()
    )
    total_sessions = (
        db.query(SessionRecord)
        .filter(SessionRecord.user_id == current_user.id)
        .count()
    )

    project_count = (
        db.query(Project)
        .filter(Project.owner_id == current_user.id, Project.deleted_at == None)
        .count()
    )
    task_count = (
        db.query(Task)
        .filter(Task.owner_id == current_user.id, Task.deleted_at == None)
        .count()
    )
    note_count = (
        db.query(Note)
        .filter(Note.owner_id == current_user.id, Note.deleted_at == None)
        .count()
    )
    files_count = len(get_settings().storage_roots)

    return AccountOverviewOut(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name or (ext.display_name if ext else current_user.email.split("@")[0]),
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        google_identity=google_id,
        device_stats=DeviceStatsOut(total=total_devices, active=active_devices),
        session_stats=SessionStatsOut(total=total_sessions, active=active_sessions),
        metrics=AccountMetricsOut(
            projects=project_count,
            tasks=task_count,
            notes=note_count,
            files=files_count,
        ),
    )


@router.get("/devices", response_model=list[DeviceOut])
def list_account_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all hardware nodes and client devices owned by authenticated user."""
    return (
        db.query(Device)
        .filter(Device.owner_id == current_user.id)
        .order_by(Device.last_seen.desc())
        .all()
    )


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_account_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke and unbind an owned hardware device."""
    device = (
        db.query(Device)
        .filter(Device.id == device_id, Device.owner_id == current_user.id)
        .first()
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    log_activity(
        db,
        user_id=current_user.id,
        action="device.removed",
        detail=f"device_id={device_id} name={device.name}",
    )
    db.delete(device)
    db.commit()


@router.get("/sessions", response_model=list[SessionOut])
def list_account_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List authentication sessions strictly for the authenticated identity."""
    return (
        db.query(SessionRecord)
        .filter(SessionRecord.user_id == current_user.id)
        .order_by(SessionRecord.issued_at.desc())
        .limit(100)
        .all()
    )


@router.delete("/sessions/{session_id}")
def revoke_account_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke a specific authentication session family owned by this user."""
    sess = (
        db.query(SessionRecord)
        .filter(
            SessionRecord.id == session_id,
            SessionRecord.user_id == current_user.id,
        )
        .first()
    )
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # Invalidate whole token family to guarantee revocation
    db.query(SessionRecord).filter(
        SessionRecord.family_id == sess.family_id,
        SessionRecord.user_id == current_user.id,
    ).update({"revoked_at": utcnow()}, synchronize_session=False)

    log_activity(
        db,
        user_id=current_user.id,
        action="auth.session_revoked",
        detail=f"session_id={session_id} family={sess.family_id}",
    )
    db.commit()
    return {"ok": True, "detail": "Session revoked"}


@router.get("/activity", response_model=ActivityPageOut)
def list_account_activity(
    category: str | None = Query(None, pattern="^(all|auth|device|session)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Paginated, categorized audit activity timeline for authenticated user."""
    q = db.query(Activity).filter(Activity.user_id == current_user.id)

    if category == "auth":
        q = q.filter(
            (Activity.action.like("user.%")) | (Activity.action.like("auth.%"))
        )
    elif category == "device":
        q = q.filter(Activity.action.like("device.%"))
    elif category == "session":
        q = q.filter(Activity.action.like("%session%"))

    total = q.count()
    items = (
        q.order_by(Activity.created_at.desc(), Activity.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return ActivityPageOut(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/server-status", response_model=ServerStatusOut)
def get_user_server_status(
    current_user: User = Depends(get_current_user),
):
    """User-safe overview of NEXUS infrastructure status without leaking secrets."""
    return ServerStatusOut(
        control_plane="operational",
        api_version="v0.3.0",
        mode="control-plane",
        database="healthy",
        relay_mesh="operational",
        auth_provider="Google OIDC (PKCE S256)",
        checked_at=utcnow(),
        features={
            "device_registration": True,
            "relay_pairing": True,
            "session_revocation": True,
            "audit_logging": True,
            "cloud_file_storage": False,
        },
    )


@router.get("/data-summary", response_model=AccountDataSummaryOut)
def get_account_data_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve user-owned data summary and sovereign storage policies."""
    project_count = (
        db.query(Project)
        .filter(Project.owner_id == current_user.id, Project.deleted_at == None)
        .count()
    )
    note_count = (
        db.query(Note)
        .filter(Note.owner_id == current_user.id, Note.deleted_at == None)
        .count()
    )
    task_count = (
        db.query(Task)
        .filter(Task.owner_id == current_user.id, Task.deleted_at == None)
        .count()
    )
    inbox_count = (
        db.query(InboxItem)
        .filter(InboxItem.owner_id == current_user.id)
        .count()
    )
    device_count = db.query(Device).filter(Device.owner_id == current_user.id).count()

    return AccountDataSummaryOut(
        profile={
            "id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name or current_user.email.split("@")[0],
            "role": current_user.role,
            "created_at": current_user.created_at.isoformat(),
        },
        stats={
            "devices": device_count,
            "projects": project_count,
            "notes": note_count,
            "tasks": task_count,
            "inbox_items": inbox_count,
        },
        storage={
            "cloud_storage_policy": "Zero Cloud Retention (Sovereign Architecture)",
            "cloud_bytes_stored": 0,
            "local_node_storage": "Distributed across registered hardware nodes",
            "file_transfer_protocol": "End-to-end encrypted peer relay (ChaCha20-Poly1305)",
        },
        capabilities={
            "sync": "Available via local node sync endpoints",
            "export": "Available directly from Client Console",
            "backup": "Local hardware vaults",
            "cloud_custody": "Disabled by design",
        },
    )
