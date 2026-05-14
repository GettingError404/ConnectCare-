"""
RBAC repositories for roles, permissions, and user-role assignments.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.models.tenant import Organization, OrganizationUnit


class PermissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_permissions(self, skip: int = 0, limit: int = 100) -> list[Permission]:
        query = select(Permission).order_by(Permission.resource, Permission.action).offset(skip).limit(limit)
        return self.db.execute(query).scalars().all()

    def get_by_id(self, permission_id: UUID) -> Optional[Permission]:
        return self.db.execute(select(Permission).where(Permission.id == permission_id)).scalar_one_or_none()

    def get_by_resource_action(self, resource: str, action: str) -> Optional[Permission]:
        return self.db.execute(
            select(Permission).where(
                and_(Permission.resource == resource, Permission.action == action)
            )
        ).scalar_one_or_none()

    def get_by_keys(self, keys: Iterable[str]) -> list[Permission]:
        key_pairs = []
        for key in keys:
            resource, action = key.split(":", 1)
            key_pairs.append((resource, action))
        if not key_pairs:
            return []
        conditions = [and_(Permission.resource == resource, Permission.action == action) for resource, action in key_pairs]
        return self.db.execute(select(Permission).where(or_(*conditions))).scalars().all()


class RoleRepository:
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def _scope_clause(self, include_system: bool = True):
        if include_system:
            return or_(Role.tenant_id == self.tenant_id, Role.tenant_id.is_(None))
        return Role.tenant_id == self.tenant_id

    def list_roles(self, skip: int = 0, limit: int = 100, include_system: bool = True) -> list[Role]:
        query = (
            select(Role)
            .options(
                selectinload(Role.permissions),
                selectinload(Role.parent_role),
            )
            .where(self._scope_clause(include_system=include_system))
            .where(Role.deleted_at.is_(None))
            .order_by(Role.is_system_role.desc(), Role.name.asc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(query).scalars().all()

    def get_by_id(self, role_id: UUID, include_system: bool = True) -> Optional[Role]:
        query = select(Role).options(selectinload(Role.permissions), selectinload(Role.parent_role)).where(Role.id == role_id)
        query = query.where(self._scope_clause(include_system=include_system))
        return self.db.execute(query).scalar_one_or_none()

    def get_by_slug(self, slug: str, include_system: bool = True) -> Optional[Role]:
        query = select(Role).where(Role.slug == slug).where(self._scope_clause(include_system=include_system))
        return self.db.execute(query).scalar_one_or_none()

    def slug_exists(self, slug: str, exclude_role_id: Optional[UUID] = None) -> bool:
        query = select(Role.id).where(Role.slug == slug).where(self._scope_clause(include_system=True))
        if exclude_role_id:
            query = query.where(Role.id != exclude_role_id)
        return self.db.execute(query).first() is not None

    def get_ancestors(self, role_id: UUID) -> list[Role]:
        ancestors: list[Role] = []
        current = self.get_by_id(role_id)
        seen: set[UUID] = set()
        while current and current.parent_role_id and current.parent_role_id not in seen:
            parent = self.get_by_id(current.parent_role_id)
            if not parent:
                break
            ancestors.append(parent)
            seen.add(parent.id)
            current = parent
        return ancestors


class UserRoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_role_id: UUID) -> Optional[UserRole]:
        return self.db.execute(
            select(UserRole)
            .options(selectinload(UserRole.role), selectinload(UserRole.user))
            .where(UserRole.id == user_role_id)
        ).scalar_one_or_none()

    def get_active_assignments(
        self,
        user_id: UUID,
        tenant_id: UUID,
        organization_id: Optional[UUID] = None,
        organization_unit_id: Optional[UUID] = None,
    ) -> list[UserRole]:
        now = datetime.now(timezone.utc)
        query = (
            select(UserRole)
            .options(
                selectinload(UserRole.role).selectinload(Role.permissions),
                selectinload(UserRole.role).selectinload(Role.parent_role),
            )
            .join(User, User.id == UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
            .where(UserRole.is_active.is_(True))
            .where(or_(UserRole.expires_at.is_(None), UserRole.expires_at > now))
            .where(or_(User.tenant_id == tenant_id, User.tenant_id.is_(None)))
            .where(or_(Role.tenant_id == tenant_id, Role.tenant_id.is_(None)))
            .where(Role.deleted_at.is_(None))
        )
        if organization_id is not None:
            query = query.where(or_(UserRole.organization_id.is_(None), UserRole.organization_id == organization_id))
        if organization_unit_id is not None:
            query = query.where(
                or_(
                    UserRole.organization_unit_id.is_(None),
                    UserRole.organization_unit_id == organization_unit_id,
                )
            )
        return self.db.execute(query).scalars().all()

    def find_exact_assignment(
        self,
        user_id: UUID,
        role_id: UUID,
        organization_id: Optional[UUID],
        organization_unit_id: Optional[UUID],
    ) -> Optional[UserRole]:
        return self.db.execute(
            select(UserRole)
            .where(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id,
                    UserRole.organization_id.is_(organization_id) if organization_id is None else UserRole.organization_id == organization_id,
                    UserRole.organization_unit_id.is_(organization_unit_id) if organization_unit_id is None else UserRole.organization_unit_id == organization_unit_id,
                )
            )
        ).scalar_one_or_none()

    def assign_role(
        self,
        user_id: UUID,
        role_id: UUID,
        assigned_by: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        organization_unit_id: Optional[UUID] = None,
        expires_at: Optional[datetime] = None,
    ) -> UserRole:
        existing = self.find_exact_assignment(user_id, role_id, organization_id, organization_unit_id)
        if existing:
            existing.is_active = True
            existing.assigned_by = assigned_by
            existing.expires_at = expires_at
            existing.assigned_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        assignment = UserRole(
            user_id=user_id,
            role_id=role_id,
            organization_id=organization_id,
            organization_unit_id=organization_unit_id,
            assigned_by=assigned_by,
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def revoke_role(self, user_role_id: UUID) -> Optional[UserRole]:
        assignment = self.get_by_id(user_role_id)
        if not assignment:
            return None
        assignment.is_active = False
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def list_user_permissions(
        self,
        user_id: UUID,
        tenant_id: UUID,
        organization_id: Optional[UUID] = None,
        organization_unit_id: Optional[UUID] = None,
    ) -> list[UserRole]:
        return self.get_active_assignments(
            user_id=user_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            organization_unit_id=organization_unit_id,
        )
