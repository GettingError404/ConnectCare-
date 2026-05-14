"""
API routes for tenant and organization management.

Endpoints:
- POST /tenants - Create tenant
- GET /tenants/{id} - Get tenant
- POST /organizations - Create organization
- GET /organizations - List organizations
- POST /organization-units - Create unit
- GET /organization-units/tree - Get hierarchy
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status, Query, Request

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tenant import Tenant, Organization, OrganizationUnit
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantDetailResponse,
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationDetailResponse,
    OrganizationUnitCreate,
    OrganizationUnitUpdate,
    OrganizationUnitResponse,
    OrganizationUnitDetailResponse,
    OrganizationUnitTreeResponse,
)
from app.services.tenant import (
    TenantService,
    OrganizationService,
    OrganizationUnitService,
)
from app.middleware.tenant_context import get_tenant_id_from_request, require_tenant_context
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/tenants", tags=["Tenants"])


# ============= Tenant Endpoints =============

@router.post("/tenants", response_model=TenantDetailResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tenant:
    """Create a new tenant. (Admin-only)"""
    service = TenantService(db)
    return service.create_tenant(payload)


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tenant:
    """Get tenant by ID. (Admin-only)"""
    service = TenantService(db)
    return service.get_tenant(tenant_id)


@router.get("/tenants", response_model=list[TenantResponse])
def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Tenant]:
    """List all active tenants. (Admin-only)"""
    service = TenantService(db)
    return service.list_tenants(skip=skip, limit=limit)


@router.patch("/tenants/{tenant_id}", response_model=TenantDetailResponse)
def update_tenant(
    tenant_id: UUID,
    payload: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tenant:
    """Update tenant. (Admin-only)"""
    service = TenantService(db)
    return service.update_tenant(tenant_id, payload)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft-delete tenant. (Admin-only)"""
    service = TenantService(db)
    service.delete_tenant(tenant_id)


# ============= Organization Endpoints =============

@router.post("/organizations", response_model=OrganizationDetailResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Organization:
    """Create a new organization in current tenant."""
    tenant_id = require_tenant_context(request)
    service = OrganizationService(db, tenant_id)
    return service.create_organization(payload)


@router.get("/organizations/{org_id}", response_model=OrganizationDetailResponse)
def get_organization(
    org_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Organization:
    """Get organization by ID."""
    tenant_id = require_tenant_context(request)
    service = OrganizationService(db, tenant_id)
    return service.get_organization(org_id)


@router.get("/organizations", response_model=list[OrganizationResponse])
def list_organizations(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Organization]:
    """List all active organizations in current tenant."""
    tenant_id = require_tenant_context(request)
    service = OrganizationService(db, tenant_id)
    return service.list_organizations(skip=skip, limit=limit)


@router.patch("/organizations/{org_id}", response_model=OrganizationDetailResponse)
def update_organization(
    org_id: UUID,
    payload: OrganizationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Organization:
    """Update organization."""
    tenant_id = require_tenant_context(request)
    service = OrganizationService(db, tenant_id)
    return service.update_organization(org_id, payload)


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft-delete organization."""
    tenant_id = require_tenant_context(request)
    service = OrganizationService(db, tenant_id)
    service.delete_organization(org_id)


# ============= Organization Unit Endpoints =============

@router.post("/organizations/{org_id}/units", response_model=OrganizationUnitDetailResponse, status_code=status.HTTP_201_CREATED)
def create_organization_unit(
    org_id: UUID,
    payload: OrganizationUnitCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationUnit:
    """Create a new organization unit."""
    tenant_id = require_tenant_context(request)
    service = OrganizationUnitService(db, tenant_id, org_id)
    return service.create_unit(payload)


@router.get("/organizations/{org_id}/units/{unit_id}", response_model=OrganizationUnitDetailResponse)
def get_organization_unit(
    org_id: UUID,
    unit_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationUnit:
    """Get organization unit by ID."""
    tenant_id = require_tenant_context(request)
    service = OrganizationUnitService(db, tenant_id, org_id)
    return service.get_unit(unit_id)


@router.get("/organizations/{org_id}/units", response_model=list[OrganizationUnitResponse])
def list_organization_units(
    org_id: UUID,
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrganizationUnit]:
    """List all active units in organization."""
    tenant_id = require_tenant_context(request)
    service = OrganizationUnitService(db, tenant_id, org_id)
    return service.list_units(skip=skip, limit=limit)


@router.get("/organizations/{org_id}/units-tree", response_model=list[OrganizationUnitTreeResponse])
def get_organization_unit_tree(
    org_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Get full organization unit hierarchy as tree."""
    tenant_id = require_tenant_context(request)
    service = OrganizationUnitService(db, tenant_id, org_id)
    return service.get_tree()


@router.patch("/organizations/{org_id}/units/{unit_id}", response_model=OrganizationUnitDetailResponse)
def update_organization_unit(
    org_id: UUID,
    unit_id: UUID,
    payload: OrganizationUnitUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationUnit:
    """Update organization unit."""
    tenant_id = require_tenant_context(request)
    service = OrganizationUnitService(db, tenant_id, org_id)
    return service.update_unit(unit_id, payload)


@router.delete("/organizations/{org_id}/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization_unit(
    org_id: UUID,
    unit_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft-delete organization unit and children."""
    tenant_id = require_tenant_context(request)
    service = OrganizationUnitService(db, tenant_id, org_id)
    service.delete_unit(unit_id)
