"""
RBAC services for role, permission, and authorization management.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.models.tenant import Organization, OrganizationUnit
from app.repositories.rbac import PermissionRepository, RoleRepository, UserRoleRepository
from app.schemas.rbac import AssignRoleRequest, PermissionResponse, RoleCreate, RoleResponse, RoleUpdate, UserRoleResponse

logger = logging.getLogger(__name__)


class PermissionLookupCache:
    def __init__(self) -> None:
        self.ttl_seconds = int(os.getenv("RBAC_CACHE_TTL_SECONDS", "30"))
        self._memory: dict[str, tuple[float, str]] = {}
        self._redis = None
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis

                self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
            except Exception:
                self._redis = None

    def get(self, key: str) -> Optional[str]:
        if self._redis is not None:
            try:
                return self._redis.get(key)
            except Exception:
                return None
        value = self._memory.get(key)
        if not value:
            return None
        expires_at, payload = value
        if datetime.now(timezone.utc).timestamp() > expires_at:
            self._memory.pop(key, None)
            return None
        return payload

    def set(self, key: str, value: str) -> None:
        if self._redis is not None:
            try:
                self._redis.setex(key, self.ttl_seconds, value)
                return
            except Exception:
                pass
        self._memory[key] = (datetime.now(timezone.utc).timestamp() + self.ttl_seconds, value)


class PermissionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PermissionRepository(db)

    def list_permissions(self, skip: int = 0, limit: int = 100) -> list[Permission]:
        return self.repository.list_permissions(skip=skip, limit=limit)

    def get_permission(self, permission_id: UUID) -> Permission:
        permission = self.repository.get_by_id(permission_id)
        if not permission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
        return permission


class RoleService:
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repository = RoleRepository(db, tenant_id)
        self.permission_repository = PermissionRepository(db)

    def _ensure_parent_valid(self, parent_role_id: Optional[UUID], role_id: Optional[UUID] = None) -> Optional[Role]:
        if parent_role_id is None:
            return None
        parent = self.repository.get_by_id(parent_role_id, include_system=True)
        if not parent or parent.is_soft_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent role not found")
        if role_id and parent.id == role_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role cannot inherit from itself")
        if role_id:
            current = parent
            seen: set[UUID] = set()
            while current and current.parent_role_id:
                if current.id in seen:
                    break
                if current.parent_role_id == role_id:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create circular role inheritance")
                seen.add(current.id)
                current = self.repository.get_by_id(current.parent_role_id, include_system=True)
        return parent

    def create_role(self, payload: RoleCreate) -> Role:
        if self.repository.slug_exists(payload.slug):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role slug already exists")

        parent = self._ensure_parent_valid(payload.parent_role_id)
        role = Role(
            tenant_id=self.tenant_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            parent_role_id=parent.id if parent else None,
            is_system_role=False,
            is_active=True,
        )
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        logger.info("role_created", extra={"tenant_id": str(self.tenant_id), "role_id": str(role.id), "slug": role.slug})
        return role

    def list_roles(self, skip: int = 0, limit: int = 100) -> list[Role]:
        return self.repository.list_roles(skip=skip, limit=limit, include_system=True)

    def get_role(self, role_id: UUID) -> Role:
        role = self.repository.get_by_id(role_id, include_system=True)
        if not role or role.is_soft_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role

    def update_role(self, role_id: UUID, payload: RoleUpdate) -> Role:
        role = self.get_role(role_id)
        if role.is_system_role and payload.slug and payload.slug != role.slug:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System role slug cannot be changed")
        if payload.slug and payload.slug != role.slug and self.repository.slug_exists(payload.slug, exclude_role_id=role.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role slug already exists")
        if "parent_role_id" in payload.model_dump(exclude_unset=True):
            parent = self._ensure_parent_valid(payload.parent_role_id, role_id=role.id)
            role.parent_role_id = parent.id if parent else None
        for field_name, value in payload.model_dump(exclude_unset=True, exclude={"parent_role_id"}).items():
            setattr(role, field_name, value)
        self.db.commit()
        self.db.refresh(role)
        logger.info("role_updated", extra={"tenant_id": str(self.tenant_id), "role_id": str(role.id)})
        return role

    def delete_role(self, role_id: UUID) -> bool:
        role = self.get_role(role_id)
        role.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
        logger.info("role_deleted", extra={"tenant_id": str(self.tenant_id), "role_id": str(role.id)})
        return True


class AuthorizationService:
    def __init__(self, db: Session):
        self.db = db
        self.user_role_repository = UserRoleRepository(db)
        self.permission_repository = PermissionRepository(db)
        self.cache = PermissionLookupCache()

    def _get_user(self, user_id: UUID) -> User:
        user = self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def validate_tenant_isolation(self, user: User, tenant_id: UUID) -> None:
        if user.tenant_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not tenant-scoped")
        if user.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access denied")

    def _scope_matches(self, assignment: UserRole, organization_id: Optional[UUID], organization_unit_id: Optional[UUID]) -> bool:
        if assignment.organization_id is not None and assignment.organization_id != organization_id:
            return False
        if assignment.organization_unit_id is not None and assignment.organization_unit_id != organization_unit_id:
            return False
        return True

    def _collect_role_permissions(self, role: Role, visited: Optional[set[UUID]] = None) -> set[str]:
        visited = visited or set()
        if role.id in visited:
            return set()
        visited.add(role.id)
        keys = {f"{permission.resource}:{permission.action}" for permission in role.permissions}
        if role.parent_role:
            keys |= self._collect_role_permissions(role.parent_role, visited)
        return keys

    def get_user_permissions(
        self,
        user_id: UUID,
        tenant_id: UUID,
        organization_id: Optional[UUID] = None,
        organization_unit_id: Optional[UUID] = None,
    ) -> list[str]:
        cache_key = f"rbac:perms:{user_id}:{tenant_id}:{organization_id}:{organization_unit_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return json.loads(cached)

        user = self._get_user(user_id)
        self.validate_tenant_isolation(user, tenant_id)

        assignments = self.user_role_repository.get_active_assignments(
            user_id=user_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            organization_unit_id=organization_unit_id,
        )
        permissions: set[str] = set()
        for assignment in assignments:
            if not self._scope_matches(assignment, organization_id, organization_unit_id):
                continue
            if assignment.role.slug == "super_admin":
                permissions.update({f"{permission.resource}:{permission.action}" for permission in self.permission_repository.list_permissions(skip=0, limit=10000)})
                break
            permissions.update(self._collect_role_permissions(assignment.role))

        result = sorted(permissions)
        self.cache.set(cache_key, json.dumps(result))
        return result

    def user_has_permission(
        self,
        user_id: UUID,
        permission: str,
        tenant_id: UUID,
        organization_id: Optional[UUID] = None,
        organization_unit_id: Optional[UUID] = None,
    ) -> bool:
        return permission in self.get_user_permissions(user_id, tenant_id, organization_id, organization_unit_id)

    def require_permission(
        self,
        user: User,
        permission: str,
        tenant_id: UUID,
        organization_id: Optional[UUID] = None,
        organization_unit_id: Optional[UUID] = None,
    ) -> None:
        if not self.user_has_permission(user.id, permission, tenant_id, organization_id, organization_unit_id):
            logger.warning(
                "permission_denied",
                extra={
                    "user_id": str(user.id),
                    "tenant_id": str(tenant_id),
                    "organization_id": str(organization_id) if organization_id else None,
                    "organization_unit_id": str(organization_unit_id) if organization_unit_id else None,
                    "permission": permission,
                },
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    def require_any_permission(
        self,
        user: User,
        permissions: list[str],
        tenant_id: UUID,
        organization_id: Optional[UUID] = None,
        organization_unit_id: Optional[UUID] = None,
    ) -> None:
        if not any(self.user_has_permission(user.id, permission, tenant_id, organization_id, organization_unit_id) for permission in permissions):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    def require_role(self, user: User, role_slug: str, tenant_id: UUID) -> None:
        assignments = self.user_role_repository.get_active_assignments(user.id, tenant_id)
        if not any(assignment.role.slug == role_slug for assignment in assignments):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role required")

    def assign_role(self, payload: AssignRoleRequest, assigned_by: Optional[UUID], tenant_id: UUID) -> UserRole:
        user = self._get_user(payload.user_id)
        if user.tenant_id is None:
            user.tenant_id = tenant_id
        elif user.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant assignment denied")

        role_repo = RoleRepository(self.db, tenant_id)
        role = role_repo.get_by_id(payload.role_id, include_system=True)
        if not role or role.is_soft_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        if role.tenant_id not in (None, tenant_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role does not belong to tenant")

        if payload.organization_id is not None:
            organization = self.db.get(Organization, payload.organization_id)
            if not organization or organization.tenant_id != tenant_id or organization.is_soft_deleted:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")
        if payload.organization_unit_id is not None:
            unit = self.db.get(OrganizationUnit, payload.organization_unit_id)
            if not unit:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization unit not found")
            if payload.organization_id and unit.organization_id != payload.organization_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization unit access denied")

        assignment = self.user_role_repository.assign_role(
            user_id=payload.user_id,
            role_id=payload.role_id,
            assigned_by=assigned_by,
            organization_id=payload.organization_id,
            organization_unit_id=payload.organization_unit_id,
            expires_at=payload.expires_at,
        )
        self.db.commit()
        self.db.refresh(user)
        logger.info(
            "role_assigned",
            extra={
                "tenant_id": str(tenant_id),
                "user_id": str(payload.user_id),
                "role_id": str(payload.role_id),
                "organization_id": str(payload.organization_id) if payload.organization_id else None,
                "organization_unit_id": str(payload.organization_unit_id) if payload.organization_unit_id else None,
            },
        )
        return assignment

    def revoke_role(self, user_role_id: UUID, tenant_id: UUID) -> UserRole:
        assignment = self.user_role_repository.get_by_id(user_role_id)
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")
        user = self._get_user(assignment.user_id)
        self.validate_tenant_isolation(user, tenant_id)
        revoked = self.user_role_repository.revoke_role(user_role_id)
        if not revoked:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")
        logger.info("role_revoked", extra={"tenant_id": str(tenant_id), "user_role_id": str(user_role_id)})
        return revoked
