import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select, func

from app.api.v1.ws_alerts import manager as ws_manager
from app.db.session import SessionLocal
from app.models.alerts import AlertEvent, AlertRule
from app.models.streams import DeviceTelemetry, VitalStreamEvent
from app.models.tenant import Tenant
from app.repositories.alerts import AlertRuleRepository
from app.services.ingest_service import IngestService
from app.services import notification_service
from app.services import event_bus as event_bus_module


def test_full_realtime_pipeline_simulation(monkeypatch):
    db = SessionLocal()
    notification_calls = []
    broadcast_calls = []
    published_events = []

    async def fake_broadcast(tenant_id: str, message: dict):
        broadcast_calls.append((tenant_id, message))

    def fake_publish(channel: str, event: dict):
        published_events.append((channel, event))
        if channel == "alerts" and event.get("tenant_id"):
            asyncio.run(fake_broadcast(event["tenant_id"], event))

    def fake_notify(channel: str, to: str, subject: str, body: str, metadata=None):
        notification_calls.append((channel, to, subject, body, metadata or {}))

    monkeypatch.setattr(event_bus_module.event_bus, "publish", fake_publish)
    monkeypatch.setattr(notification_service.NotificationService, "notify", staticmethod(fake_notify))

    try:
        tenant = Tenant(name=f"Pipeline Tenant {uuid4().hex[:8]}", slug=f"pipeline-{uuid4().hex[:8]}")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        rule_repo = AlertRuleRepository(db, tenant.id)
        rule = rule_repo.add(
            AlertRule(
                tenant_id=tenant.id,
                name="High heart rate",
                metric_name="heart_rate",
                operator=">",
                threshold_value=100.0,
                severity="high",
                duration_seconds=0,
                cooldown_seconds=30,
                enabled=True,
            )
        )

        ingest = IngestService(db, tenant.id)
        payload = {
            "tenant_id": str(tenant.id),
            "event_id": f"evt-{uuid4().hex}",
            "event_timestamp": datetime.now(timezone.utc).isoformat(),
            "source_topic": f"vitals/{tenant.id}/elder-{uuid4().hex[:6]}",
            "payload": {
                "heart_rate": 124.0,
                "spo2": 97.0,
                "battery_level": 88,
                "signal_strength": 73,
            },
        }

        first_event = ingest.persist_event(payload, source_topic=payload["source_topic"])
        assert first_event.tenant_id == tenant.id

        telemetry_count = db.execute(select(func.count()).select_from(DeviceTelemetry).where(DeviceTelemetry.tenant_id == tenant.id)).scalar_one()
        alert_count = db.execute(select(func.count()).select_from(AlertEvent).where(AlertEvent.tenant_id == tenant.id)).scalar_one()
        stream_count = db.execute(select(func.count()).select_from(VitalStreamEvent).where(VitalStreamEvent.tenant_id == tenant.id)).scalar_one()

        assert telemetry_count == 1
        assert stream_count == 1
        assert alert_count == 1
        assert published_events, "Expected event bus publishes"
        assert any(channel == "alerts" for channel, _ in published_events)
        assert notification_calls, "Expected notification job to be queued"
        assert broadcast_calls and broadcast_calls[0][0] == str(tenant.id)

        # duplicate within cooldown should not create a second telemetry row or alert
        duplicate_event = ingest.persist_event(payload, source_topic=payload["source_topic"])
        assert duplicate_event.is_duplicate is True

        telemetry_count_after = db.execute(select(func.count()).select_from(DeviceTelemetry).where(DeviceTelemetry.tenant_id == tenant.id)).scalar_one()
        alert_count_after = db.execute(select(func.count()).select_from(AlertEvent).where(AlertEvent.tenant_id == tenant.id)).scalar_one()
        assert telemetry_count_after == 1
        assert alert_count_after == 1
    finally:
        db.rollback()
        db.close()
