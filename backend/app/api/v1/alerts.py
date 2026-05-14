from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.alert import AlertResponse
from app.services.alert_service import get_user_alerts, resolve_alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/me", response_model=list[AlertResponse])
def list_my_alerts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_user_alerts(db=db, user=current_user)


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_my_alert(alert_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return resolve_alert(db=db, alert_id=alert_id, user=current_user)
