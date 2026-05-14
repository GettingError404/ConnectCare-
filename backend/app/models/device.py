import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.health_vitals import HealthVital
    from app.models.user import User


class Device(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("device_identifier", name="uq_devices_device_identifier"),
    )

    # Ownership & multi-tenant scoping
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    elder_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("elders.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_caregiver_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("caregivers.id", ondelete="SET NULL"), nullable=True, index=True)

    # Identity
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    serial_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    device_type: Mapped[str] = mapped_column(String(64), nullable=False)
    device_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    device_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Metadata
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    firmware_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    battery_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    signal_strength: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_seen_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    device_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    connectivity_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Authentication
    device_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    certificate_fingerprint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mqtt_client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    user: Mapped["User"] = relationship(back_populates="devices")
    health_vitals: Mapped[list["HealthVital"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
    )
