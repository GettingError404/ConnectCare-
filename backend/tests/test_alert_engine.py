import os
import pytest
from datetime import datetime

from app.db.session import SessionLocal
from app.repositories.alerts import AlertRuleRepository, AlertEventRepository
from app.schemas.alerts import AlertRuleCreate


@pytest.mark.skipif(os.getenv("DATABASE_URL") is None, reason="No DATABASE_URL configured")
def test_threshold_trigger_creates_alert():
    db = SessionLocal()
    try:
        tenant = db.execute("SELECT id FROM tenants LIMIT 1").scalar_one_or_none()
        if not tenant:
            pytest.skip("No tenant available")

        repo = AlertRuleRepository(db, tenant)
        # cleanup existing rules for metric
        # create rule
        r = repo.model(
            tenant_id=tenant,
            name="HR high",
            metric_name="heart_rate",
            operator=">",
            threshold_value=100.0,
            severity="high",
            duration_seconds=0,
            cooldown_seconds=1,
            enabled=True,
        )
        repo.add(r)

        # evaluate via engine
        from app.services.alert_engine import AlertEngine

        ae = AlertEngine(db, tenant)
        ae.evaluate_telemetry({"heart_rate": 120.0, "elder_id": None})

        evr = AlertEventRepository(db, tenant)
        events = evr.get_recent(3600)
        assert any(e.metric_name == "heart_rate" for e in events)

    finally:
        db.close()
