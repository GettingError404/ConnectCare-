from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.device import DeviceRegister, DeviceResponse
from app.services.device_service import register_device, get_devices_for_user
from app.models.user import User

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/register", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def register_device_endpoint(payload: DeviceRegister, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return register_device(db=db, payload=payload, user=current_user)


@router.get("/me", response_model=list[DeviceResponse])
def get_my_devices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_devices_for_user(db=db, user=current_user)
