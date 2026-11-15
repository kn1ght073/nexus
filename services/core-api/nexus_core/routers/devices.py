"""Device registry: register, list, heartbeat, remove."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import log_activity, publish_event
from ..database import get_db
from ..models import Device, User
from ..schemas import DeviceCreate, DeviceOut
from ..security import get_current_user

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def register_device(
    device_in: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = Device(
        name=device_in.name,
        platform=device_in.platform,
        capabilities=",".join(device_in.capabilities),
        owner_id=current_user.id,
        is_online=True,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    log_activity(db, user_id=current_user.id, action="device.registered", detail=f"{device.name} ({device.platform})", device_id=device.id)
    publish_event("DEVICE_REGISTERED", current_user.id, {"device_id": device.id, "name": device.name})
    db.commit()
    return device


@router.get("", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Device)
        .filter(Device.owner_id == current_user.id)
        .order_by(Device.last_seen.desc())
        .all()
    )


@router.post("/{device_id}/heartbeat", response_model=DeviceOut)
def heartbeat(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = (
        db.query(Device)
        .filter(Device.id == device_id, Device.owner_id == current_user.id)
        .first()
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    device.is_online = True
    from ..models import utcnow

    device.last_seen = utcnow()
    db.commit()
    db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = (
        db.query(Device)
        .filter(Device.id == device_id, Device.owner_id == current_user.id)
        .first()
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    log_activity(db, user_id=current_user.id, action="device.removed", detail=device.name)
    db.delete(device)
    db.commit()
