"""
Tenant-aware repository implementations for multi-tenant isolation.

This module provides base classes for implementing tenant-scoped repository patterns
that automatically prevent cross-tenant access and ensure data isolation.
"""

from typing import TypeVar, Generic, Optional, Type
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.tenant import Tenant, Organization, OrganizationUnit

T = TypeVar("T")


class TenantAwareRepository(Generic[T]):
    """Base repository with automatic tenant-scoping for queries."""

    def __init__(self, db: Session, model: Type[T], tenant_id: UUID):
        """Initialize repository with tenant context.

        Args:
            db: SQLAlchemy session
            model: ORM model class
            tenant_id: Tenant ID for automatic scoping
        """
        self.db = db
        self.model = model
        self.tenant_id = tenant_id

    def _get_tenant_filter(self):
        """Get the filter clause for current tenant.

        Override in subclasses to customize tenant filtering logic.
        """
        if hasattr(self.model, "tenant_id"):
            return self.model.tenant_id == self.tenant_id
        return None

    def get_by_id(self, obj_id: UUID) -> Optional[T]:
        """Get object by ID, scoped to current tenant."""
        tenant_filter = self._get_tenant_filter()
        query = select(self.model).where(self.model.id == obj_id)
        if tenant_filter is not None:
            query = query.where(tenant_filter)
        return self.db.execute(query).scalar_one_or_none()

    def list_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """List all objects for current tenant."""
        tenant_filter = self._get_tenant_filter()
        query = select(self.model)
        if tenant_filter is not None:
            query = query.where(tenant_filter)
        query = query.offset(skip).limit(limit)
        return self.db.execute(query).scalars().all()

    def add(self, obj: T) -> T:
        """Add and commit object."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj_id: UUID, data: dict) -> Optional[T]:
        """Update object, scoped to current tenant."""
        obj = self.get_by_id(obj_id)
        if not obj:
            return None
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj_id: UUID) -> bool:
        """Soft-delete object if supported, hard-delete otherwise."""
        obj = self.get_by_id(obj_id)
        if not obj:
            return False

        if hasattr(obj, "deleted_at"):
            # Soft delete
            from datetime import datetime
            from sqlalchemy import func

            obj.deleted_at = datetime.now()
        else:
            # Hard delete
            self.db.delete(obj)

        self.db.commit()
        return True


class TenantRepository(TenantAwareRepository[Tenant]):
    """Repository for Tenant model."""

    def __init__(self, db: Session):
        """Initialize with global context (no tenant_id needed)."""
        self.db = db
        self.model = Tenant

    def _get_tenant_filter(self):
        """Tenants are not tenant-scoped."""
        return None

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        return self.db.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()

    def get_active(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """Get active (non-deleted) tenants."""
        return self.db.execute(
            select(Tenant).where(Tenant.deleted_at.is_(None)).offset(skip).limit(limit)
        ).scalars().all()


class OrganizationRepository(TenantAwareRepository[Organization]):
    """Repository for Organization model, scoped to tenant."""

    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, Organization, tenant_id)

    def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug within current tenant."""
        return self.db.execute(
            select(Organization).where(
                and_(
                    Organization.tenant_id == self.tenant_id,
                    Organization.slug == slug,
                )
            )
        ).scalar_one_or_none()

    def get_active(self, skip: int = 0, limit: int = 100) -> list[Organization]:
        """Get active organizations for current tenant."""
        return self.db.execute(
            select(Organization)
            .where(
                and_(
                    Organization.tenant_id == self.tenant_id,
                    Organization.deleted_at.is_(None),
                )
            )
            .offset(skip)
            .limit(limit)
        ).scalars().all()


class OrganizationUnitRepository(TenantAwareRepository[OrganizationUnit]):
    """Repository for OrganizationUnit model, scoped to tenant and organization."""

    def __init__(self, db: Session, tenant_id: UUID, organization_id: UUID):
        """Initialize with tenant and organization context."""
        super().__init__(db, OrganizationUnit, tenant_id)
        self.organization_id = organization_id

    def _get_tenant_filter(self):
        """Filter by organization (which implicitly ties to tenant)."""
        return OrganizationUnit.organization_id == self.organization_id

    def get_by_id(self, obj_id: UUID) -> Optional[OrganizationUnit]:
        """Get unit by ID, ensuring it belongs to current organization."""
        return self.db.execute(
            select(OrganizationUnit).where(
                and_(
                    OrganizationUnit.id == obj_id,
                    OrganizationUnit.organization_id == self.organization_id,
                )
            )
        ).scalar_one_or_none()

    def get_root_units(self) -> list[OrganizationUnit]:
        """Get root units (no parent) for current organization."""
        return self.db.execute(
            select(OrganizationUnit).where(
                and_(
                    OrganizationUnit.organization_id == self.organization_id,
                    OrganizationUnit.parent_id.is_(None),
                )
            )
        ).scalars().all()

    def get_children(self, parent_id: UUID) -> list[OrganizationUnit]:
        """Get direct children of a unit."""
        parent = self.get_by_id(parent_id)
        if not parent:
            return []
        return self.db.execute(
            select(OrganizationUnit).where(
                OrganizationUnit.parent_id == parent_id
            )
        ).scalars().all()

    def get_subtree(self, root_id: UUID) -> dict:
        """Get full subtree starting from given unit (for tree view)."""
        root = self.get_by_id(root_id)
        if not root:
            return {}

        def build_tree(unit: OrganizationUnit) -> dict:
            children = self.db.execute(
                select(OrganizationUnit).where(OrganizationUnit.parent_id == unit.id)
            ).scalars().all()
            return {
                "id": unit.id,
                "name": unit.name,
                "description": unit.description,
                "level": unit.level,
                "is_active": unit.is_active,
                "children": [build_tree(child) for child in children],
            }

        return build_tree(root)

    def validate_parent_belongs_to_org(self, parent_id: UUID) -> bool:
        """Ensure parent unit belongs to same organization (prevent cross-org links)."""
        return self.get_by_id(parent_id) is not None

    def prevent_circular_hierarchy(self, unit_id: UUID, proposed_parent_id: UUID) -> bool:
        """Check if setting proposed_parent_id as parent would create a cycle."""
        if unit_id == proposed_parent_id:
            return False  # Unit cannot be its own parent

        # Walk up the hierarchy from proposed parent to check if we hit the unit
        current = self.get_by_id(proposed_parent_id)
        while current:
            if current.id == unit_id:
                return False  # Cycle detected
            if current.parent_id is None:
                break
            current = self.get_by_id(current.parent_id)

        return True  # No cycle
