import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, insert, select
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.health_vitals import HealthVital, MetricType as DBMetricType
from app.models.user import User
from app.schemas.health_vitals import HealthVitalBatchCreate, HealthVitalCreate, MetricType

logger = logging.getLogger(__name__)


def _ensure_user_exists(db: Session, user_id: UUID) -> None:
    user_exists = db.execute(select(User.id).where(User.id == user_id)).scalar_one_or_none()
    if user_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


def _ensure_device_exists(db: Session, device_id: UUID, user_id: UUID) -> None:
    device_exists = db.execute(
        select(Device.id).where(Device.id == device_id, Device.user_id == user_id)
    ).scalar_one_or_none()
    if device_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found for user",
        )


def create_vital(db: Session, payload: HealthVitalCreate) -> HealthVital:
    _ensure_user_exists(db, payload.user_id)
    _ensure_device_exists(db, payload.device_id, payload.user_id)

    vital = HealthVital(
        user_id=payload.user_id,
        device_id=payload.device_id,
        metric_type=DBMetricType(payload.metric_type.value),
        value=payload.value,
        unit=payload.unit,
        recorded_at=payload.recorded_at,
    )

    try:
        db.add(vital)
        db.commit()
        db.refresh(vital)
        # enqueue background processing (non-blocking)
        try:
            from app.tasks.vitals_tasks import process_vital_data

            # send to Celery; if broker not available, do not fail the request
            process_vital_data.delay(str(vital.id))
        except Exception:
            logger.exception("Failed to enqueue vital processing task")

        return vital
    except (IntegrityError, DataError) as exc:
        db.rollback()
        logger.warning("Failed to create vital due to invalid payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vital payload")
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while creating vital: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


def create_vitals_batch(db: Session, payload: HealthVitalBatchCreate) -> dict[str, int]:
    records = payload.root
    if not records:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch payload cannot be empty")

    user_ids = {item.user_id for item in records}
    existing_user_ids = set(db.execute(select(User.id).where(User.id.in_(user_ids))).scalars().all())
    missing_users = user_ids - existing_user_ids
    if missing_users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    device_pairs = {(item.device_id, item.user_id) for item in records}
    device_ids = {pair[0] for pair in device_pairs}
    valid_devices = set(
        db.execute(select(Device.id, Device.user_id).where(Device.id.in_(device_ids))).all()
    )
    missing_device_pairs = device_pairs - valid_devices
    if missing_device_pairs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more devices not found for their users",
        )

    rows = [
        {
            "user_id": item.user_id,
            "device_id": item.device_id,
            "metric_type": DBMetricType(item.metric_type.value),
            "value": item.value,
            "unit": item.unit,
            "recorded_at": item.recorded_at,
        }
        for item in records
    ]

    try:
        db.execute(insert(HealthVital), rows)
        db.commit()
        return {"inserted_count": len(rows)}
    except (IntegrityError, DataError) as exc:
        db.rollback()
        logger.warning("Failed to batch insert vitals due to invalid payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid batch payload")
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while batch inserting vitals: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


def get_user_vitals(
    db: Session,
    user_id: UUID,
    metric_type: MetricType | None,
    limit: int,
) -> list[HealthVital]:
    try:
        _ensure_user_exists(db, user_id)

        query = select(HealthVital).where(HealthVital.user_id == user_id)
        if metric_type is not None:
            query = query.where(HealthVital.metric_type == DBMetricType(metric_type.value))

        query = query.order_by(HealthVital.recorded_at.desc()).limit(limit)
        return db.execute(query).scalars().all()
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Database error while fetching user vitals: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


def get_latest_vitals(db: Session, user_id: UUID) -> list[HealthVital]:
    try:
        _ensure_user_exists(db, user_id)

        ranked = (
            select(
                HealthVital.id.label("id"),
                HealthVital.recorded_at.label("recorded_at"),
                func.row_number()
                .over(
                    partition_by=HealthVital.metric_type,
                    order_by=HealthVital.recorded_at.desc(),
                )
                .label("rn"),
            )
            .where(HealthVital.user_id == user_id)
            .subquery()
        )

        query = (
            select(HealthVital)
            .join(
                ranked,
                (HealthVital.id == ranked.c.id)
                & (HealthVital.recorded_at == ranked.c.recorded_at),
            )
            .where(ranked.c.rn == 1)
            .order_by(HealthVital.metric_type.asc())
        )

        return db.execute(query).scalars().all()
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Database error while fetching latest vitals: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
