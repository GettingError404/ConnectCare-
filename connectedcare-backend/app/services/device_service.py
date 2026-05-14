from typing import List

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.user import User
from app.schemas.device import DeviceRegister


def register_device(db: Session, payload: DeviceRegister, user: User) -> Device:
    # prevent duplicates by device_name+type for the same user
    exists = (
        db.query(Device)
        .filter(Device.user_id == user.id, Device.device_name == payload.device_name, Device.device_type == payload.device_type.value)
        .one_or_none()
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device already registered")

    device = Device(
        user_id=user.id,
        device_identifier=payload.device_identifier or payload.device_name,
        device_type=payload.device_type.value,
        device_name=payload.device_name,
        manufacturer=payload.manufacturer,
    )
    try:
        db.add(device)
        db.commit()
        db.refresh(device)
        return device
    except IntegrityError as exc:
        db.rollback()
        if "uq_devices_device_identifier" in str(exc.orig):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device identifier already registered")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register device")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register device")


def get_devices_for_user(db: Session, user: User) -> List[Device]:
    return db.query(Device).filter(Device.user_id == user.id).order_by(Device.created_at.desc()).all()
