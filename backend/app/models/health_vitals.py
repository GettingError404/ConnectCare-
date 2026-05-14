import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, Float, ForeignKey, Index, String, UniqueConstraint, desc, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.device import Device
    from app.models.user import User


class MetricType(str, Enum):
    steps = "steps"
    heart_rate = "heart_rate"
    sleep = "sleep"
    calories = "calories"
    spo2 = "spo2"
    respiratory_rate = "respiratory_rate"
    body_temperature = "body_temperature"


class HealthVital(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "health_vitals"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "metric_type",
            "recorded_at",
            name="uq_health_vitals_device_metric_recorded_at",
        ),
        Index("ix_health_vitals_user_recorded_at_desc", "user_id", desc("recorded_at")),
        Index("ix_health_vitals_metric_type", "metric_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        unique=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_type: Mapped[MetricType] = mapped_column(
        SQLEnum(MetricType, name="metric_type_enum", native_enum=True),
        nullable=False,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(back_populates="health_vitals")
    device: Mapped["Device"] = relationship(back_populates="health_vitals")
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="vital",
        cascade="all, delete-orphan",
    )
