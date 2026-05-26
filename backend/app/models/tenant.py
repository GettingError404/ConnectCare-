"""
Multi-tenant domain models for ConnectedCare.

Provides:
- Tenant: top-level tenant with global configuration
- Organization: sub-organization within a tenant
- OrganizationUnit: hierarchical organizational units
"""

from typing import TYPE_CHECKING, Optional
from datetime import datetime
import uuid

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.auth import UserSession
    from app.models.rbac import Role, UserRole


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Top-level tenant entity. Each customer organization is a tenant."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    organizations: Mapped[list["Organization"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        foreign_keys="Organization.tenant_id",
    )
    users: Mapped[list["User"]] = relationship(
        back_populates="tenant",
        foreign_keys="User.tenant_id",
        lazy="selectin",
    )
    user_sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="tenant",
        foreign_keys="UserSession.tenant_id",
        lazy="selectin",
    )
    roles: Mapped[list["Role"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        foreign_keys="Role.tenant_id",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_tenants_slug", "slug"),
        Index("idx_tenants_is_active", "is_active"),
        Index("idx_tenants_deleted_at", "deleted_at"),
    )

    @property
    def is_soft_deleted(self) -> bool:
        """Check if tenant is soft-deleted."""
        return self.deleted_at is not None


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Organization within a tenant."""

    __tablename__ = "organizations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        back_populates="organizations",
        foreign_keys=[tenant_id],
    )
    organization_units: Mapped[list["OrganizationUnit"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationUnit.organization_id",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="organization",
        foreign_keys="UserRole.organization_id",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_organizations_tenant_id", "tenant_id"),
        Index("idx_organizations_tenant_slug", "tenant_id", "slug"),
        Index("idx_organizations_is_active", "is_active"),
        Index("idx_organizations_deleted_at", "deleted_at"),
    )

    @property
    def is_soft_deleted(self) -> bool:
        """Check if organization is soft-deleted."""
        return self.deleted_at is not None


class OrganizationUnit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Hierarchical organizational unit (department, team, etc.)."""

    __tablename__ = "organization_units"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(nullable=False, default=0)  # 0=root, 1=department, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="organization_units",
        foreign_keys=[organization_id],
    )
    parent: Mapped[Optional["OrganizationUnit"]] = relationship(
        remote_side=lambda: [OrganizationUnit.id],
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children: Mapped[list["OrganizationUnit"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationUnit.parent_id",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="organization_unit",
        foreign_keys="UserRole.organization_unit_id",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_org_units_organization_id", "organization_id"),
        Index("idx_org_units_parent_id", "parent_id"),
        Index("idx_org_units_org_parent", "organization_id", "parent_id"),
        Index("idx_org_units_is_active", "is_active"),
        Index("idx_org_units_deleted_at", "deleted_at"),
    )

    @property
    def is_soft_deleted(self) -> bool:
        """Check if organization unit is soft-deleted."""
        return self.deleted_at is not None

    @property
    def is_root(self) -> bool:
        """Check if this is a root unit (no parent)."""
        return self.parent_id is None
