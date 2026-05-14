from __future__ import annotations

import logging
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.ingest_service import IngestService
from app.services.event_bus import event_bus
from app.core.logging import get_logger

try:
    from prometheus_client import Counter
except Exception:  # pragma: no cover - metrics scaffold only
    Counter = None

logger = logging.getLogger(__name__)

ingestion_received_total = Counter("connectedcare_ingestion_received_total", "Total ingestion payloads received", ["stage"]) if Counter else None
ingestion_failed_total = Counter("connectedcare_ingestion_failed_total", "Total ingestion payloads failed", ["reason"]) if Counter else None


def _extract_tenant_id(payload: dict) -> UUID | None:
    tenant_id = payload.get("tenant_id")
    if tenant_id:
        try:
            return UUID(str(tenant_id))
        except Exception:
            return None

    source_topic = payload.get("source_topic") or ""
    parts = source_topic.split("/")
    if len(parts) >= 2 and parts[0] == "vitals":
        try:
            return UUID(parts[1])
        except Exception:
            return None
    return None


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 3})
def process_vital_message(self, payload: dict):
    """Celery task to ingest an incoming vital payload (from MQTT or REST).

    Payload should include tenant_id and source_topic so tenant isolation is preserved.
    """
    if ingestion_received_total:
        ingestion_received_total.labels(stage="received").inc()

    db: Session = SessionLocal()
    try:
        tenant_id = _extract_tenant_id(payload)
        if not tenant_id:
            logger.warning("Missing or invalid tenant_id in payload", extra={"source_topic": payload.get("source_topic")})
            if ingestion_failed_total:
                ingestion_failed_total.labels(reason="missing_tenant_id").inc()
            event_bus.publish(
                "events",
                {
                    "type": "ingestion.failed",
                    "reason": "missing_tenant_id",
                    "source_topic": payload.get("source_topic"),
                },
            )
            return
        logger.info("Processing vital payload", extra={"tenant_id": str(tenant_id), "source_topic": payload.get("source_topic")})
        svc = IngestService(db, tenant_id)
        svc.persist_event(payload.get("payload") if payload.get("payload") else payload, source_topic=payload.get("source_topic"))
    except Exception as exc:
        if ingestion_failed_total:
            ingestion_failed_total.labels(reason="exception").inc()
        try:
            tenant_id = _extract_tenant_id(payload)
            if tenant_id:
                IngestService(db, tenant_id).log_failure(payload.get("device_id"), payload.get("event_id"), payload, str(exc))
        except Exception:
            logger.exception("Failed to write dead-letter record")
        logger.exception("Failed to process vital message: %s", exc, extra={"source_topic": payload.get("source_topic")})
        raise self.retry(exc=exc)
    finally:
        db.close()
