from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.repositories.tenant import TenantAwareRepository
from app.models.streams import (
    VitalStreamEvent,
    DeviceTelemetry,
    VitalAnomaly,
    VitalThreshold,
    DeviceHeartbeat,
    IngestionFailureLog,
)


class VitalStreamEventRepository(TenantAwareRepository[VitalStreamEvent]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, VitalStreamEvent, tenant_id)

    def get_recent_for_elder(self, elder_id: UUID, limit: int = 100) -> List[VitalStreamEvent]:
        return self.db.execute(
            select(VitalStreamEvent).where(and_(VitalStreamEvent.tenant_id == self.tenant_id, VitalStreamEvent.elder_id == elder_id)).order_by(VitalStreamEvent.event_timestamp.desc()).limit(limit)
        ).scalars().all()


class DeviceTelemetryRepository(TenantAwareRepository[DeviceTelemetry]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, DeviceTelemetry, tenant_id)

    def get_latest_for_elder(self, elder_id: UUID, limit: int = 100):
        return self.db.execute(
            select(DeviceTelemetry).where(and_(DeviceTelemetry.tenant_id == self.tenant_id, DeviceTelemetry.elder_id == elder_id)).order_by(DeviceTelemetry.recorded_at.desc()).limit(limit)
        ).scalars().all()


class VitalThresholdRepository(TenantAwareRepository[VitalThreshold]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, VitalThreshold, tenant_id)

    def get_for_elder(self, elder_id: UUID):
        return self.db.execute(select(VitalThreshold).where(and_(VitalThreshold.tenant_id == self.tenant_id, VitalThreshold.elder_id == elder_id))).scalar_one_or_none()
