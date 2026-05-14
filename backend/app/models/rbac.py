"""
RBAC domain models for ConnectedCare.

Provides role, permission, role-permission mapping, and user-role assignment
models with tenant-safe scoping and support for role inheritance.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.tenant import Organization, OrganizationUnit
    from app.models.tenant import Tenant
    from app.models.user import User


class Permission(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "permissions"

    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    roles: Mapped[list["Role"]] = relationship(
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin",
        overlaps="role_permissions",
    )

    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
        Index("idx_permissions_resource_action", "resource", "action"),
    )

    @property
    def key(self) -> str:
        return f"{self.resource}:{self.action}"


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    tenant_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    parent_role_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    tenant: Mapped[Optional["Tenant"]] = relationship(
        back_populates="roles",
        foreign_keys=[tenant_id],
        lazy="selectin",
    )
    parent_role: Mapped[Optional["Role"]] = relationship(
        remote_side=lambda: [Role.id],
        back_populates="child_roles",
        foreign_keys=[parent_role_id],
        lazy="selectin",
    )
    child_roles: Mapped[list["Role"]] = relationship(
        back_populates="parent_role",
        foreign_keys="Role.parent_role_id",
        lazy="selectin",
    )
    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
        overlaps="role_permissions",
    )
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
        overlaps="permissions,roles",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_roles_tenant_slug"),
        Index("idx_roles_tenant_id", "tenant_id"),
        Index("idx_roles_tenant_slug", "tenant_id", "slug"),
        Index("idx_roles_parent_role_id", "parent_role_id"),
        Index("idx_roles_is_active", "is_active"),
        Index("idx_roles_deleted_at", "deleted_at"),
    )

    @property
    def is_soft_deleted(self) -> bool:
        return self.deleted_at is not None


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped["Role"] = relationship(back_populates="role_permissions", lazy="selectin", overlaps="permissions,roles")
    permission: Mapped["Permission"] = relationship(back_populates="role_permissions", lazy="selectin", overlaps="permissions,roles")


class UserRole(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    organization_unit_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organization_units.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    assigned_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    user: Mapped["User"] = relationship(
        back_populates="user_roles",
        foreign_keys=[user_id],
        lazy="selectin",
    )
    role: Mapped["Role"] = relationship(
        back_populates="user_roles",
        foreign_keys=[role_id],
        lazy="selectin",
    )
    organization: Mapped[Optional["Organization"]] = relationship(
        foreign_keys=[organization_id],
        lazy="selectin",
        overlaps="user_roles",
    )
    organization_unit: Mapped[Optional["OrganizationUnit"]] = relationship(
        foreign_keys=[organization_unit_id],
        lazy="selectin",
        overlaps="user_roles",
    )
    assigned_by_user: Mapped[Optional["User"]] = relationship(
        foreign_keys=[assigned_by],
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_user_roles_user_id", "user_id"),
        Index("idx_user_roles_role_id", "role_id"),
        Index("idx_user_roles_organization_id", "organization_id"),
        Index("idx_user_roles_organization_unit_id", "organization_unit_id"),
        Index("idx_user_roles_is_active", "is_active"),
        Index("idx_user_roles_expires_at", "expires_at"),
        Index("idx_user_roles_user_scope", "user_id", "organization_id", "organization_unit_id"),
    )

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= datetime.utcnow()
