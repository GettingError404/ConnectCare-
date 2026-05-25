from __future__ import annotations

from datetime import datetime
import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, ForeignKey, Index, DateTime, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenant import Organization
    from app.models.user import User


class Operator(enum.Enum):
    gt = ">"
    gte = ">="
    lt = "<"
    lte = "<="
    eq = "=="


class Severity(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(enum.Enum):
    triggered = "triggered"
    acknowledged = "acknowledged"
    resolved = "resolved"


class TargetType(enum.Enum):
    user = "user"
    group = "group"
    role = "role"


class DeliveryChannel(enum.Enum):
    websocket = "websocket"
    email = "email"
    sms = "sms"
    push = "push"


class AlertRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alert_rules"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(8), nullable=False)
    threshold_value: Mapped[float] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(nullable=False, server_default="0")
    cooldown_seconds: Mapped[int] = mapped_column(nullable=False, server_default="60")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    organization: Mapped[Optional["Organization"]] = relationship(lazy="selectin")
    created_by_user: Mapped[Optional["User"]] = relationship(back_populates="created_alert_rules", lazy="selectin", foreign_keys=[created_by])
    alert_events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="alert_rule",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("operator IN ('>', '>=', '<', '<=', '==')", name="ck_alert_rules_operator"),
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="ck_alert_rules_severity"),
    )


class AlertEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alert_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    elder_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id"), nullable=True, index=True)
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("devices.id"), nullable=True, index=True)
    telemetry_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    alert_rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("alert_rules.id"), nullable=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="triggered")
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, name="metadata")

    alert_rule: Mapped[Optional["AlertRule"]] = relationship(back_populates="alert_events", lazy="selectin")
    escalations: Mapped[list["AlertEscalation"]] = relationship(
        back_populates="alert_event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="ck_alert_events_severity"),
        CheckConstraint("status IN ('triggered', 'acknowledged', 'resolved')", name="ck_alert_events_status"),
    )


class AlertEscalation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alert_escalations"

    alert_event_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("alert_events.id"), nullable=False, index=True)
    escalation_level: Mapped[int] = mapped_column(nullable=False, server_default="1")
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    delivery_channel: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    alert_event: Mapped[Optional["AlertEvent"]] = relationship(back_populates="escalations", lazy="selectin")

    __table_args__ = (
        CheckConstraint("target_type IN ('user', 'group', 'role')", name="ck_alert_escalations_target_type"),
        CheckConstraint(
            "delivery_channel IN ('websocket', 'email', 'sms', 'push')",
            name="ck_alert_escalations_delivery_channel",
        ),
    )


Index("idx_alert_rule_tenant_metric", AlertRule.tenant_id, AlertRule.metric_name)
Index("idx_alert_event_tenant_time", AlertEvent.tenant_id, AlertEvent.triggered_at)
Index("idx_alert_event_elder", AlertEvent.tenant_id, AlertEvent.elder_id)
