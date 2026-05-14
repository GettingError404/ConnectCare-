import os
import pytest
from uuid import UUID
from datetime import date

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.tenant import Tenant
from app.services.healthcare import ElderService
from app.schemas.healthcare import ElderCreate


def _get_any_tenant_id(session):
    row = session.execute(select(Tenant.id)).scalar_one_or_none()
    return row


@pytest.mark.skipif(os.getenv("DATABASE_URL") is None, reason="No DATABASE_URL configured")
def test_elder_create_and_medical_profile_auto_create():
    session = SessionLocal()
    try:
        tenant_id = _get_any_tenant_id(session)
        if not tenant_id:
            pytest.skip("No tenant available to run test against")

        svc = ElderService(session, tenant_id)
        payload = ElderCreate(
            medical_record_number=f"TEST-MRN-{os.urandom(4).hex()}",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1940, 1, 1),
        )
        elder = svc.create_elder(payload)
        assert elder is not None
        # medical profile should exist
        mp = svc.mp_repo.get_by_elder(elder.id)
        assert mp is not None

        # duplicate MRN should conflict
        with pytest.raises(Exception):
            svc.create_elder(payload)
    finally:
        session.close()
