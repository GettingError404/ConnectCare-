import hashlib
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.repositories.streams import VitalStreamEventRepository, DeviceTelemetryRepository, VitalThresholdRepository
from app.services.event_bus import event_bus
from app.models.streams import IngestionFailureLog, DeviceTelemetry, VitalAnomaly
from app.core.config import settings
from app.services.alert_engine import AlertEngine

logger = logging.getLogger(__name__)

try:
    import redis
except Exception:
    redis = None


class IngestService:
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.event_repo = VitalStreamEventRepository(db, tenant_id)
        self.telemetry_repo = DeviceTelemetryRepository(db, tenant_id)
        self.threshold_repo = VitalThresholdRepository(db, tenant_id)
        self._redis = None
        if redis and settings.REDIS_URL:
            try:
                self._redis = redis.from_url(settings.REDIS_URL)
            except Exception:
                logger.exception("Failed to init redis for ingest service")

    def _checksum(self, payload: dict) -> str:
        data = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def is_duplicate(self, checksum: str, event_id: Optional[str]) -> bool:
        # try event_id uniqueness first
        key = f"dedupe:{self.tenant_id}:{event_id or checksum}"
        try:
            if self._redis:
                # setnx returns 1 if set
                was_set = self._redis.setnx(key, "1")
                if was_set:
                    self._redis.expire(key, 60 * 60)  # 1 hour dedupe window
                    return False
                return True
        except Exception:
            logger.exception("Redis dedupe failed")
        # fallback: check DB for checksum
        existing = self.db.execute(select(self.event_repo.model).where(self.event_repo.model.checksum == checksum)).scalar_one_or_none()
        return existing is not None

    def persist_event(self, event_payload: dict, source_topic: Optional[str] = None):
        event_id = event_payload.get("event_id")
        checksum = self._checksum(event_payload)
        duplicate = self.is_duplicate(checksum, event_id)

        # write stream event record
        event = self.event_repo.add(self.event_repo.model(
            tenant_id=self.tenant_id,
            elder_id=event_payload.get("elder_id"),
            device_id=event_payload.get("device_id"),
            event_id=event_id,
            event_timestamp=event_payload.get("event_timestamp") or datetime.utcnow(),
            ingestion_timestamp=datetime.utcnow(),
            source_topic=source_topic,
            payload=event_payload.get("payload"),
            checksum=checksum,
            is_duplicate=duplicate,
            raw_payload=json.dumps(event_payload),
        ))

        try:
            from app.core import metrics
            if duplicate:
                metrics.inc_ingest_duplicate(tenant=str(self.tenant_id))
                metrics.inc_ingest(result="duplicate", tenant=str(self.tenant_id))
            else:
                metrics.inc_ingest(result="persisted", tenant=str(self.tenant_id))
        except Exception:
            pass

        if duplicate:
            event_bus.publish("events", {"type": "duplicate.detected", "tenant_id": str(self.tenant_id), "event_id": event_id or checksum})
            logger.info("Duplicate event detected", extra={"checksum": checksum, "event_id": event_id})
            return event

        # validate minimal telemetry structure
        telemetry = event_payload.get("payload", {})
        telemetry_record = self.telemetry_repo.add(self.telemetry_repo.model(
            tenant_id=self.tenant_id,
            elder_id=event_payload.get("elder_id"),
            device_id=event_payload.get("device_id"),
            recorded_at=event_payload.get("event_timestamp") or datetime.utcnow(),
            heart_rate=telemetry.get("heart_rate"),
            spo2=telemetry.get("spo2"),
            systolic_bp=telemetry.get("systolic_bp"),
            diastolic_bp=telemetry.get("diastolic_bp"),
            respiratory_rate=telemetry.get("respiratory_rate"),
            glucose_level=telemetry.get("glucose_level"),
            ecg_signal=telemetry.get("ecg_signal"),
            body_temperature=telemetry.get("body_temperature"),
            battery_level=telemetry.get("battery_level"),
            signal_strength=telemetry.get("signal_strength"),
            fall_detected=telemetry.get("fall_detected"),
            stress_level=telemetry.get("stress_level"),
            sleep_quality=telemetry.get("sleep_quality"),
        ))

        # publish events
        event_bus.publish("events", {"type": "vital.received", "tenant_id": str(self.tenant_id), "elder_id": str(event_payload.get("elder_id")) if event_payload.get("elder_id") else None, "telemetry_id": str(telemetry_record.id)})

        # evaluate alerts asynchronously/synchronously
        try:
            try:
                ae = AlertEngine(self.db, self.tenant_id)
                ae.evaluate_telemetry({**telemetry, "elder_id": event_payload.get("elder_id"), "device_id": event_payload.get("device_id")}, telemetry_record.id)
            except Exception:
                logger.exception("AlertEngine evaluation failed")
        except Exception:
            logger.exception("Failed to run alert evaluation")

        # basic anomaly detection via thresholds
        try:
            thresh = self.threshold_repo.get_for_elder(event_payload.get("elder_id"))
            hr = telemetry.get("heart_rate")
            if thresh and hr is not None:
                if thresh.max_heart_rate and hr > thresh.max_heart_rate:
                    self._record_anomaly("high_heart_rate", "critical", hr, {"max": thresh.max_heart_rate})
                if thresh.min_heart_rate and hr < thresh.min_heart_rate:
                    self._record_anomaly("low_heart_rate", "warning", hr, {"min": thresh.min_heart_rate})
        except Exception:
            logger.exception("Failed threshold check")

        return event

    def _record_anomaly(self, anomaly_type: str, severity: str, value: float, expected: dict):
        try:
            an = VitalAnomaly(
                tenant_id=self.tenant_id,
                anomaly_type=anomaly_type,
                severity=severity,
                detected_value=value,
                expected_range=expected,
                detection_source="threshold",
            )
            self.db.add(an)
            self.db.commit()
            event_bus.publish("events", {"type": "anomaly.detected", "tenant_id": str(self.tenant_id), "anomaly_id": str(an.id)})
        except Exception:
            self.db.rollback()
            logger.exception("Failed to persist anomaly")

    def log_failure(self, device_id: Optional[UUID], event_id: Optional[str], payload: dict, error: str):
        try:
            self.db.add(IngestionFailureLog(tenant_id=self.tenant_id, device_id=device_id, event_id=event_id, error=error, payload=payload))
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception("Failed to record ingestion failure")
