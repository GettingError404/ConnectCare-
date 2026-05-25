import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.alert import Alert
    from app.models.alerts import AlertRule
    from app.models.health_vitals import HealthVital
    from app.models.auth import RefreshToken, UserSession
    from app.models.healthcare import CarePlan, ConsentRecord
    from app.models.rbac import UserRole
    from app.models.tenant import Tenant


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    tenant: Mapped[Optional["Tenant"]] = relationship(
        back_populates="users",
        foreign_keys=[tenant_id],
        lazy="selectin",
    )

    devices: Mapped[list["Device"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    health_vitals: Mapped[list["HealthVital"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    created_alert_rules: Mapped[list["AlertRule"]] = relationship(
        back_populates="created_by_user",
        lazy="selectin",
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserRole.user_id",
        lazy="selectin",
    )
    care_plans_created: Mapped[list["CarePlan"]] = relationship(
        back_populates="created_by_user",
        foreign_keys="CarePlan.created_by",
        lazy="selectin",
    )
    consents_granted_to: Mapped[list["ConsentRecord"]] = relationship(
        back_populates="granted_to_user",
        foreign_keys="ConsentRecord.granted_to_user_id",
        lazy="selectin",
    )
    consents_granted_by: Mapped[list["ConsentRecord"]] = relationship(
        back_populates="granted_by_user",
        foreign_keys="ConsentRecord.granted_by_user_id",
        lazy="selectin",
    )
