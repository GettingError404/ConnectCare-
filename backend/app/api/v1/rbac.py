"""
API routes for RBAC management.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.dependencies.authorization import require_any_permission, require_permission, require_role
from app.db.session import get_db
from app.models.rbac import Permission, Role, UserRole
from app.models.user import User
from app.schemas.rbac import AssignRoleRequest, PermissionResponse, RoleCreate, RoleResponse, RoleUpdate, UserRoleResponse
from app.services.rbac import AuthorizationService, PermissionService, RoleService

router = APIRouter(prefix="/rbac", tags=["RBAC"])


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_permission("permissions:view")),
    db: Session = Depends(get_db),
) -> list[Permission]:
    service = PermissionService(db)
    return service.list_permissions(skip=skip, limit=limit)


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    request: Request,
    current_user: User = Depends(require_permission("roles:manage")),
    db: Session = Depends(get_db),
) -> Role:
    tenant_id = request.state.tenant_id
    service = RoleService(db, tenant_id)
    return service.create_role(payload)


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_permission("roles:view")),
    db: Session = Depends(get_db),
) -> list[Role]:
    tenant_id = request.state.tenant_id
    service = RoleService(db, tenant_id)
    return service.list_roles(skip=skip, limit=limit)


@router.get("/roles/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission("roles:view")),
    db: Session = Depends(get_db),
) -> Role:
    tenant_id = request.state.tenant_id
    service = RoleService(db, tenant_id)
    return service.get_role(role_id)


@router.patch("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    request: Request,
    current_user: User = Depends(require_permission("roles:manage")),
    db: Session = Depends(get_db),
) -> Role:
    tenant_id = request.state.tenant_id
    service = RoleService(db, tenant_id)
    return service.update_role(role_id, payload)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission("roles:manage")),
    db: Session = Depends(get_db),
) -> None:
    tenant_id = request.state.tenant_id
    service = RoleService(db, tenant_id)
    service.delete_role(role_id)


@router.post("/user-roles", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
def assign_role(
    payload: AssignRoleRequest,
    request: Request,
    current_user: User = Depends(require_permission("user_roles:manage")),
    db: Session = Depends(get_db),
) -> UserRole:
    tenant_id = request.state.tenant_id
    service = AuthorizationService(db)
    return service.assign_role(payload, assigned_by=current_user.id, tenant_id=tenant_id)


@router.delete("/user-roles/{user_role_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_role(
    user_role_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission("user_roles:manage")),
    db: Session = Depends(get_db),
) -> None:
    tenant_id = request.state.tenant_id
    service = AuthorizationService(db)
    service.revoke_role(user_role_id, tenant_id)


@router.get("/user-roles/users/{user_id}/permissions", response_model=list[str])
def get_user_permissions(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission("users:view")),
    db: Session = Depends(get_db),
) -> list[str]:
    tenant_id = request.state.tenant_id
    service = AuthorizationService(db)
    return service.get_user_permissions(user_id, tenant_id)
