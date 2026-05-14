from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session

from app.repositories.tenant import TenantAwareRepository
from app.models.alerts import AlertRule, AlertEvent, AlertEscalation


class AlertRuleRepository(TenantAwareRepository[AlertRule]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, AlertRule, tenant_id)

    def list_active(self) -> List[AlertRule]:
        return self.db.execute(select(AlertRule).where(and_(AlertRule.tenant_id == self.tenant_id, AlertRule.enabled == True))).scalars().all()


class AlertEventRepository(TenantAwareRepository[AlertEvent]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, AlertEvent, tenant_id)

    def get_unresolved_for_rule(self, rule_id: UUID) -> List[AlertEvent]:
        return self.db.execute(select(AlertEvent).where(and_(AlertEvent.tenant_id == self.tenant_id, AlertEvent.alert_rule_id == rule_id, AlertEvent.status != 'resolved'))).scalars().all()

    def get_recent(self, since_seconds: int = 3600, limit: int = 100) -> List[AlertEvent]:
        since = datetime.utcnow() - timedelta(seconds=since_seconds)
        return self.db.execute(select(AlertEvent).where(and_(AlertEvent.tenant_id == self.tenant_id, AlertEvent.triggered_at >= since)).order_by(desc(AlertEvent.triggered_at)).limit(limit)).scalars().all()

    def add_event(self, event: AlertEvent) -> AlertEvent:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event


class AlertEscalationRepository(TenantAwareRepository[AlertEscalation]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, AlertEscalation, tenant_id)

    def list_for_event(self, alert_event_id: UUID) -> List[AlertEscalation]:
        return self.db.execute(select(AlertEscalation).where(and_(AlertEscalation.alert_event_id == alert_event_id))).scalars().all()
