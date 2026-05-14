"""
Services for tenant and organization domain management.

Provides CRUD operations with business logic validation and tenant isolation.
"""

import logging
from uuid import UUID
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.tenant import Tenant, Organization, OrganizationUnit
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationUnitCreate,
    OrganizationUnitUpdate,
)
from app.repositories.tenant import (
    TenantRepository,
    OrganizationRepository,
    OrganizationUnitRepository,
)

logger = logging.getLogger(__name__)


# ============= Tenant Services =============

class TenantService:
    """Service for tenant CRUD and management."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = TenantRepository(db)

    def create_tenant(self, payload: TenantCreate) -> Tenant:
        """Create a new tenant.

        Args:
            payload: TenantCreate schema

        Returns:
            Created Tenant object

        Raises:
            HTTPException: If slug already exists
        """
        # Check if slug already exists
        existing = self.repository.get_by_slug(payload.slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tenant with slug '{payload.slug}' already exists",
            )

        tenant = Tenant(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            is_active=True,
        )

        logger.info(
            "tenant_created",
            extra={"tenant_id": str(tenant.id), "slug": payload.slug},
        )
        return self.repository.add(tenant)

    def get_tenant(self, tenant_id: UUID) -> Tenant:
        """Get tenant by ID.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Tenant object

        Raises:
            HTTPException: If tenant not found or soft-deleted
        """
        tenant = self.repository.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )
        if tenant.is_soft_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant has been deleted",
            )
        return tenant

    def list_tenants(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """List all active tenants."""
        return self.repository.get_active(skip=skip, limit=limit)

    def update_tenant(self, tenant_id: UUID, payload: TenantUpdate) -> Tenant:
        """Update tenant.

        Args:
            tenant_id: Tenant UUID
            payload: TenantUpdate schema

        Returns:
            Updated Tenant object

        Raises:
            HTTPException: If tenant not found
        """
        tenant = self.get_tenant(tenant_id)

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tenant, key, value)

        self.db.commit()
        self.db.refresh(tenant)

        logger.info(
            "tenant_updated",
            extra={"tenant_id": str(tenant_id)},
        )
        return tenant

    def delete_tenant(self, tenant_id: UUID) -> bool:
        """Soft-delete tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            True if deleted successfully

        Raises:
            HTTPException: If tenant not found
        """
        tenant = self.get_tenant(tenant_id)
        tenant.deleted_at = datetime.now()
        self.db.commit()

        logger.info(
            "tenant_deleted",
            extra={"tenant_id": str(tenant_id)},
        )
        return True


# ============= Organization Services =============

class OrganizationService:
    """Service for organization CRUD and management."""

    def __init__(self, db: Session, tenant_id: UUID):
        """Initialize with tenant context.

        Args:
            db: SQLAlchemy session
            tenant_id: Current tenant UUID
        """
        self.db = db
        self.tenant_id = tenant_id
        self.repository = OrganizationRepository(db, tenant_id)
        self.tenant_repo = TenantRepository(db)

    def _verify_tenant_exists(self) -> Tenant:
        """Verify tenant exists and is not deleted."""
        tenant = self.tenant_repo.get_by_id(self.tenant_id)
        if not tenant or tenant.is_soft_deleted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid tenant context",
            )
        return tenant

    def create_organization(self, payload: OrganizationCreate) -> Organization:
        """Create a new organization.

        Args:
            payload: OrganizationCreate schema

        Returns:
            Created Organization object

        Raises:
            HTTPException: If slug exists in tenant or tenant invalid
        """
        self._verify_tenant_exists()

        # Check if slug already exists in tenant
        existing = self.repository.get_by_slug(payload.slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Organization with slug '{payload.slug}' already exists",
            )

        org = Organization(
            tenant_id=self.tenant_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            is_active=True,
        )

        logger.info(
            "organization_created",
            extra={
                "tenant_id": str(self.tenant_id),
                "org_id": str(org.id),
                "slug": payload.slug,
            },
        )
        return self.repository.add(org)

    def get_organization(self, org_id: UUID) -> Organization:
        """Get organization by ID within tenant.

        Args:
            org_id: Organization UUID

        Returns:
            Organization object

        Raises:
            HTTPException: If not found, deleted, or not in current tenant
        """
        org = self.repository.get_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        if org.is_soft_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization has been deleted",
            )
        return org

    def list_organizations(self, skip: int = 0, limit: int = 100) -> list[Organization]:
        """List all active organizations in tenant."""
        return self.repository.get_active(skip=skip, limit=limit)

    def update_organization(self, org_id: UUID, payload: OrganizationUpdate) -> Organization:
        """Update organization.

        Args:
            org_id: Organization UUID
            payload: OrganizationUpdate schema

        Returns:
            Updated Organization object

        Raises:
            HTTPException: If organization not found or not in tenant
        """
        org = self.get_organization(org_id)

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(org, key, value)

        self.db.commit()
        self.db.refresh(org)

        logger.info(
            "organization_updated",
            extra={"tenant_id": str(self.tenant_id), "org_id": str(org_id)},
        )
        return org

    def delete_organization(self, org_id: UUID) -> bool:
        """Soft-delete organization.

        Args:
            org_id: Organization UUID

        Returns:
            True if deleted successfully

        Raises:
            HTTPException: If organization not found or not in tenant
        """
        org = self.get_organization(org_id)
        org.deleted_at = datetime.now()
        self.db.commit()

        logger.info(
            "organization_deleted",
            extra={"tenant_id": str(self.tenant_id), "org_id": str(org_id)},
        )
        return True


# ============= Organization Unit Services =============

class OrganizationUnitService:
    """Service for organization unit hierarchy management."""

    def __init__(self, db: Session, tenant_id: UUID, organization_id: UUID):
        """Initialize with tenant and organization context.

        Args:
            db: SQLAlchemy session
            tenant_id: Current tenant UUID
            organization_id: Current organization UUID
        """
        self.db = db
        self.tenant_id = tenant_id
        self.organization_id = organization_id
        self.repository = OrganizationUnitRepository(db, tenant_id, organization_id)
        self.org_repo = OrganizationRepository(db, tenant_id)

    def _verify_organization_exists(self) -> Organization:
        """Verify organization exists and belongs to tenant."""
        org = self.org_repo.get_by_id(self.organization_id)
        if not org or org.is_soft_deleted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid organization context",
            )
        return org

    def create_unit(self, payload: OrganizationUnitCreate) -> OrganizationUnit:
        """Create a new organization unit.

        Args:
            payload: OrganizationUnitCreate schema

        Returns:
            Created OrganizationUnit object

        Raises:
            HTTPException: If organization invalid, parent not found, or hierarchy invalid
        """
        self._verify_organization_exists()

        # Verify parent belongs to same organization
        level = 0
        if payload.parent_id:
            parent = self.repository.get_by_id(payload.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent organization unit not found",
                )
            level = parent.level + 1

        unit = OrganizationUnit(
            organization_id=self.organization_id,
            parent_id=payload.parent_id,
            name=payload.name,
            description=payload.description,
            level=level,
            is_active=True,
        )

        logger.info(
            "org_unit_created",
            extra={
                "tenant_id": str(self.tenant_id),
                "org_id": str(self.organization_id),
                "unit_id": str(unit.id),
                "level": level,
            },
        )
        return self.repository.add(unit)

    def get_unit(self, unit_id: UUID) -> OrganizationUnit:
        """Get organization unit by ID.

        Args:
            unit_id: OrganizationUnit UUID

        Returns:
            OrganizationUnit object

        Raises:
            HTTPException: If not found, deleted, or not in current organization
        """
        unit = self.repository.get_by_id(unit_id)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization unit not found",
            )
        if unit.is_soft_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization unit has been deleted",
            )
        return unit

    def list_units(self, skip: int = 0, limit: int = 100) -> list[OrganizationUnit]:
        """List all active units in organization."""
        return self.repository.list_all(skip=skip, limit=limit)

    def get_tree(self) -> list[dict]:
        """Get full organization unit hierarchy as trees.

        Returns list of root units with nested children.
        """
        roots = self.repository.get_root_units()
        return [self.repository.get_subtree(root.id) for root in roots]

    def update_unit(self, unit_id: UUID, payload: OrganizationUnitUpdate) -> OrganizationUnit:
        """Update organization unit.

        Args:
            unit_id: OrganizationUnit UUID
            payload: OrganizationUnitUpdate schema

        Returns:
            Updated OrganizationUnit object

        Raises:
            HTTPException: If unit not found, parent invalid, or hierarchy would have cycle
        """
        unit = self.get_unit(unit_id)

        # Validate new parent if provided
        if payload.parent_id is not None and payload.parent_id != unit.parent_id:
            if payload.parent_id:
                parent = self.repository.get_by_id(payload.parent_id)
                if not parent:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Parent organization unit not found",
                    )

                # Check for circular hierarchy
                if not self.repository.prevent_circular_hierarchy(unit_id, payload.parent_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot create circular hierarchy",
                    )

                # Update level based on new parent
                unit.level = parent.level + 1
            else:
                # Moving to root
                unit.level = 0

        update_data = payload.model_dump(exclude_unset=True, exclude={"parent_id"})
        for key, value in update_data.items():
            setattr(unit, key, value)

        if payload.parent_id is not None:
            unit.parent_id = payload.parent_id

        self.db.commit()
        self.db.refresh(unit)

        logger.info(
            "org_unit_updated",
            extra={
                "tenant_id": str(self.tenant_id),
                "org_id": str(self.organization_id),
                "unit_id": str(unit_id),
            },
        )
        return unit

    def delete_unit(self, unit_id: UUID) -> bool:
        """Soft-delete organization unit and its children.

        Args:
            unit_id: OrganizationUnit UUID

        Returns:
            True if deleted successfully

        Raises:
            HTTPException: If unit not found or not in current organization
        """
        unit = self.get_unit(unit_id)
        now = datetime.now()

        # Soft-delete the unit and all descendants
        def soft_delete_recursive(u: OrganizationUnit):
            u.deleted_at = now
            for child in u.children:
                soft_delete_recursive(child)

        soft_delete_recursive(unit)
        self.db.commit()

        logger.info(
            "org_unit_deleted",
            extra={
                "tenant_id": str(self.tenant_id),
                "org_id": str(self.organization_id),
                "unit_id": str(unit_id),
            },
        )
        return True
