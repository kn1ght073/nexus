"""Activity timeline: append-only log of every mutating action."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Activity, User
from ..schemas import ActivityOut
from ..security import get_current_user

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=list[ActivityOut])
def list_activity(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return (
        db.query(Activity)
        .filter(Activity.user_id == current_user.id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
