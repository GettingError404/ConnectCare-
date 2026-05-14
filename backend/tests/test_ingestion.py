import os
import pytest
from datetime import datetime
from app.db.session import SessionLocal
from app.services.ingest_service import IngestService


@pytest.mark.skipif(os.getenv("DATABASE_URL") is None, reason="No DATABASE_URL configured")
def test_basic_ingest_creates_telemetry():
    db = SessionLocal()
    try:
        # find any tenant
        tenant = db.execute("SELECT id FROM tenants LIMIT 1").scalar_one_or_none()
        if not tenant:
            pytest.skip("No tenant available")

        svc = IngestService(db, tenant)
        payload = {
            "event_id": "test-evt-1",
            "event_timestamp": datetime.utcnow().isoformat(),
            "elder_id": None,
            "device_id": None,
            "payload": {"heart_rate": 72.5, "spo2": 98.0},
        }
        evt = svc.persist_event(payload)
        assert evt is not None
    finally:
        db.close()
