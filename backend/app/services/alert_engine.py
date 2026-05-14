from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID

try:
    import redis
except Exception:
    redis = None

from app.core.config import settings
from app.repositories.alerts import AlertRuleRepository, AlertEventRepository
from app.models.alerts import AlertEvent, AlertRule
from app.services.event_bus import event_bus
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class AlertEngine:
    def __init__(self, db, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.rule_repo = AlertRuleRepository(db, tenant_id)
        self.event_repo = AlertEventRepository(db, tenant_id)
        self._redis = None
        if redis and settings.REDIS_URL:
            try:
                self._redis = redis.from_url(settings.REDIS_URL)
            except Exception:
                logger.exception("Failed to init redis for AlertEngine")

    def evaluate_telemetry(self, telemetry: Dict[str, Any], telemetry_record_id: Optional[UUID] = None):
        """Evaluate incoming telemetry against active alert rules."""
        rules = self.rule_repo.list_active()
        for r in rules:
            try:
                metric = r.metric_name
                if metric not in telemetry:
                    continue
                value = telemetry.get(metric)
                if value is None:
                    continue

                if self._matches(r.operator, value, r.threshold_value):
                    # check cooldown/deduplicate
                    if self._in_cooldown(r.id):
                        logger.debug("Rule in cooldown", extra={"rule_id": str(r.id)})
                        try:
                            from app.core import metrics
                            metrics.inc_alert_cooldown_skipped(tenant=str(self.tenant_id))
                        except Exception:
                            pass
                        continue

                    # create alert event
                    evt = AlertEvent(
                        tenant_id=self.tenant_id,
                        elder_id=telemetry.get("elder_id"),
                        device_id=telemetry.get("device_id"),
                        telemetry_id=telemetry_record_id,
                        alert_rule_id=r.id,
                        metric_name=metric,
                        metric_value=value,
                        severity=r.severity,
                        status="triggered",
                        triggered_at=datetime.utcnow(),
                        metadata={"rule": r.name},
                    )
                    self.event_repo.add_event(evt)
                    event_bus.publish("alerts", {"type": "alert.triggered", "tenant_id": str(self.tenant_id), "alert_id": str(evt.id)})
                    try:
                        from app.core import metrics
                        metrics.inc_alert_triggered(severity=r.severity or "unknown", tenant=str(self.tenant_id))
                    except Exception:
                        pass
                    try:
                        NotificationService().notify(
                            "websocket",
                            str(self.tenant_id),
                            "alert.triggered",
                            f"{metric}={value} exceeded threshold {r.threshold_value}",
                            {"alert_id": str(evt.id), "rule_id": str(r.id)},
                        )
                    except Exception:
                        logger.exception("Failed to queue alert notification")
                    self._set_cooldown(r.id, r.cooldown_seconds)
            except Exception:
                logger.exception("Failed evaluating rule %s", getattr(r, "id", None))

    def _matches(self, operator: str, value: float, threshold: float) -> bool:
        try:
            if operator == ">":
                return value > threshold
            if operator == ">=":
                return value >= threshold
            if operator == "<":
                return value < threshold
            if operator == "<=":
                return value <= threshold
            if operator == "==":
                return value == threshold
        except Exception:
            return False
        return False

    def _cooldown_key(self, rule_id: UUID) -> str:
        return f"alert:cooldown:{self.tenant_id}:{rule_id}"

    def _in_cooldown(self, rule_id: UUID) -> bool:
        if not self._redis:
            return False
        try:
            return self._redis.exists(self._cooldown_key(rule_id)) == 1
        except Exception:
            return False

    def _set_cooldown(self, rule_id: UUID, seconds: int):
        if not self._redis:
            return
        try:
            self._redis.set(self._cooldown_key(rule_id), "1", ex=seconds)
        except Exception:
            logger.exception("Failed to set cooldown")

    def acknowledge_alert(self, alert_id: UUID, user_id: Optional[UUID] = None):
        evt = self.event_repo.get_by_id(alert_id)
        if not evt:
            return None
        evt.status = "acknowledged"
        evt.acknowledged_at = datetime.utcnow()
        self.db.commit()
        event_bus.publish("alerts", {"type": "alert.acknowledged", "tenant_id": str(self.tenant_id), "alert_id": str(evt.id)})
        return evt

    def resolve_alert(self, alert_id: UUID):
        evt = self.event_repo.get_by_id(alert_id)
        if not evt:
            return None
        evt.status = "resolved"
        evt.resolved_at = datetime.utcnow()
        self.db.commit()
        event_bus.publish("alerts", {"type": "alert.resolved", "tenant_id": str(self.tenant_id), "alert_id": str(evt.id)})
        return evt

    # simple device checks
    def device_offline_detection(self, device_id: UUID, last_seen_at: datetime, offline_after_seconds: int = 300):
        if (datetime.utcnow() - last_seen_at).total_seconds() > offline_after_seconds:
            event_bus.publish("alerts", {"type": "device.offline", "tenant_id": str(self.tenant_id), "device_id": str(device_id)})

    def battery_low_detection(self, device_id: UUID, battery_level: int, threshold: int = 20):
        if battery_level is not None and battery_level <= threshold:
            event_bus.publish("alerts", {"type": "device.battery_low", "tenant_id": str(self.tenant_id), "device_id": str(device_id), "battery_level": battery_level})
