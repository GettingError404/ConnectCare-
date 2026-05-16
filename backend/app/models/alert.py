import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, ForeignKeyConstraint, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.health_vitals import HealthVital
    from app.models.user import User


class Alert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["vital_id", "vital_recorded_at"],
            ["health_vitals.id", "health_vitals.recorded_at"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "user_id",
            "vital_id",
            "vital_recorded_at",
            "alert_type",
            name="uq_alerts_user_vital_recorded_at_type",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vital_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    vital_recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    user: Mapped["User"] = relationship(back_populates="alerts")
    vital: Mapped["HealthVital"] = relationship(back_populates="alerts")
