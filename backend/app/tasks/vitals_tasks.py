import logging
import time
from datetime import datetime
from uuid import UUID

from celery import Task
from sqlalchemy import select

from app.core.alert_rules import evaluate_alert_rules
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.health_vitals import HealthVital
from app.services.alert_service import create_alert

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_vital_data(self: Task, vital_id: str, vital_recorded_at: str) -> None:
    """Background processing for a HealthVital record.

    Fetches vital, logs processing steps and is retried on exception with backoff.
    """
    db = SessionLocal()
    try:
        recorded_at = datetime.fromisoformat(vital_recorded_at)
        logger.info("task_start", extra={"vital_id": vital_id, "vital_recorded_at": vital_recorded_at})
        vital = db.execute(
            select(HealthVital).where(
                HealthVital.id == UUID(vital_id),
                HealthVital.recorded_at == recorded_at,
            )
        ).scalar_one_or_none()
        if not vital:
            logger.warning("vital_not_found", extra={"vital_id": vital_id, "vital_recorded_at": vital_recorded_at})
            return

        user_id = str(vital.user_id)
        logger.info(
            "processing_vital",
            extra={"vital_id": vital_id, "user_id": user_id, "metric_type": str(vital.metric_type), "value": float(vital.value)},
        )

        # simulated processing
        time.sleep(0.1)

        matched_rules = evaluate_alert_rules(str(vital.metric_type), float(vital.value))
        if not matched_rules:
            logger.info("no_alert_triggered", extra={"vital_id": vital_id, "user_id": user_id})
            logger.info("task_success", extra={"vital_id": vital_id, "user_id": user_id})
            return

        for rule in matched_rules:
            alert = create_alert(
                db=db,
                user_id=vital.user_id,
                vital_id=vital.id,
                vital_recorded_at=vital.recorded_at,
                alert_type=rule.alert_type,
                severity=rule.severity,
                message=rule.message,
            )
            logger.warning(
                "alert_created",
                extra={
                    "vital_id": vital_id,
                    "vital_recorded_at": vital_recorded_at,
                    "user_id": user_id,
                    "alert_id": str(alert.id),
                    "alert_type": rule.alert_type,
                    "severity": rule.severity,
                },
            )

        logger.info("processing_complete", extra={"vital_id": vital_id, "vital_recorded_at": vital_recorded_at, "user_id": user_id})
        logger.info("task_success", extra={"vital_id": vital_id, "vital_recorded_at": vital_recorded_at, "user_id": user_id})
    except Exception as exc:
        logger.exception("task_failure", exc_info=exc, extra={"vital_id": vital_id, "vital_recorded_at": vital_recorded_at})
        # autoretry_for will handle retries; re-raise to let Celery retry
        raise
    finally:
        db.close()
