import logging
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.user import User

logger = logging.getLogger(__name__)


def create_alert(
    db: Session,
    user_id: UUID,
    vital_id: UUID,
    vital_recorded_at: datetime,
    alert_type: str,
    severity: str,
    message: str,
) -> Alert:
    existing = (
        db.query(Alert)
        .filter(
            Alert.user_id == user_id,
            Alert.vital_id == vital_id,
            Alert.vital_recorded_at == vital_recorded_at,
            Alert.alert_type == alert_type,
        )
        .one_or_none()
    )
    if existing is not None:
        return existing

    alert = Alert(
        user_id=user_id,
        vital_id=vital_id,
        vital_recorded_at=vital_recorded_at,
        alert_type=alert_type,
        severity=severity,
        message=message,
        is_resolved=False,
    )
    try:
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info(
            "alert_created",
            extra={
                "user_id": str(user_id),
                "vital_id": str(vital_id),
                "vital_recorded_at": vital_recorded_at.isoformat() if hasattr(vital_recorded_at, "isoformat") else str(vital_recorded_at),
                "alert_type": alert_type,
                "severity": severity,
            },
        )
        return alert
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "failed_to_create_alert",
            exc_info=exc,
            extra={
                "user_id": str(user_id),
                "vital_id": str(vital_id),
                "vital_recorded_at": vital_recorded_at.isoformat() if hasattr(vital_recorded_at, "isoformat") else str(vital_recorded_at),
            },
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


def get_user_alerts(db: Session, user: User) -> list[Alert]:
    return (
        db.query(Alert)
        .filter(Alert.user_id == user.id)
        .order_by(Alert.created_at.desc())
        .all()
    )


def resolve_alert(db: Session, alert_id: UUID, user: User) -> Alert:
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user.id).one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    try:
        alert.is_resolved = True
        db.commit()
        db.refresh(alert)
        return alert
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "failed_to_resolve_alert",
            exc_info=exc,
            extra={"user_id": str(user.id), "alert_id": str(alert_id)},
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
