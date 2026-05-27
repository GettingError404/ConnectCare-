"""Idempotent RBAC seeding + default-role assignment.

Ensures:
- Required permissions exist globally (system-level)
- Required roles exist globally (admin/doctor/user)
- Admin role has the required permissions

Also provides helper to assign default 'user' role to newly registered users.

Note: this code assumes you have run migrations that create RBAC tables.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.repositories.rbac import PermissionRepository, RoleRepository, UserRoleRepository

logger = logging.getLogger(__name__)


class DefaultRBAC:
    DEFAULT_ROLES: list[dict] = [
        {"slug": "admin", "name": "Admin", "description": "Administrator Role", "parent": None},
        {"slug": "doctor", "name": "Doctor", "description": "Clinical access", "parent": "admin"},
        {"slug": "user", "name": "User", "description": "Default user role", "parent": "doctor"},
    ]

    REQUIRED_PERMISSIONS: list[dict] = [
        {"resource": "permissions", "action": "view"},
        {"resource": "roles", "action": "view"},
        {"resource": "roles", "action": "manage"},
        {"resource": "users", "action": "view"},
        {"resource": "user_roles", "action": "manage"},
    ]


def _list_all_roles_including_system(db: Session) -> list[Role]:
    # RoleRepository is tenant-scoped but its list_roles has include_system=True.
    # We pass any UUID (won't be used for system roles) and still include_system.
    dummy_tenant_id = UUID("00000000-0000-0000-0000-000000000000")
    repo = RoleRepository(db, dummy_tenant_id)
    return repo.list_roles(skip=0, limit=10_000, include_system=True)


def ensure_default_rbac_seed(db: Session, tenant_id: Optional[UUID] = None) -> None:
    """Idempotently ensure required system RBAC seed exists."""

    # 1) Permissions (global)
    perm_repo = PermissionRepository(db)
    existing_permissions = {(p.resource, p.action): p for p in perm_repo.list_permissions(skip=0, limit=10_000)}

    for spec in DefaultRBAC.REQUIRED_PERMISSIONS:
        key = (spec["resource"], spec["action"])
        if key not in existing_permissions:
            db.add(
                Permission(
                    resource=spec["resource"],
                    action=spec["action"],
                    description=None,
                )
            )

    db.flush()

    # refresh map
    existing_permissions = {(p.resource, p.action): p for p in perm_repo.list_permissions(skip=0, limit=10_000)}

    # 2) Roles (global/system)
    roles = _list_all_roles_including_system(db)
    roles_by_slug = {r.slug: r for r in roles}

    # Create missing roles as system roles (tenant_id=None)
    created: dict[str, Role] = {}
    for spec in DefaultRBAC.DEFAULT_ROLES:
        role = roles_by_slug.get(spec["slug"])
        if role is None:
            role = Role(
                tenant_id=None,
                parent_role_id=None,
                name=spec["name"],
                slug=spec["slug"],
                description=spec["description"],
                is_system_role=True,
                is_active=True,
            )
            db.add(role)
            db.flush()
        created[spec["slug"]] = role

    # Reload updated roles_by_slug for parent links
    roles_by_slug.update(created)

    # 3) Parent role inheritance
    for spec in DefaultRBAC.DEFAULT_ROLES:
        role = roles_by_slug[spec["slug"]]
        parent_slug = spec["parent"]
        if parent_slug is None:
            continue
        parent = roles_by_slug.get(parent_slug)
        if not parent:
            raise HTTPException(status_code=500, detail=f"Missing parent role: {parent_slug}")
        if role.parent_role_id != parent.id:
            role.parent_role_id = parent.id

    db.flush()

    # 4) Ensure admin has required permissions
    admin_role = roles_by_slug["admin"]
    existing_admin_perm_ids = {
        rp.permission_id
        for rp in db.query(RolePermission).filter(RolePermission.role_id == admin_role.id).all()
    }

    for spec in DefaultRBAC.REQUIRED_PERMISSIONS:
        perm = existing_permissions[(spec["resource"], spec["action"])]
        if perm.id not in existing_admin_perm_ids:
            db.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))

    db.commit()

    logger.info(
        "rbac_seed_ensured",
        extra={
            "admin_role_id": str(admin_role.id),
            "tenant_id": str(tenant_id) if tenant_id else None,
        },
    )


def assign_default_role_to_user(db: Session, user_id: UUID, tenant_id: UUID) -> UserRole:
    """Assign default 'user' role if user has no active roles."""

    ensure_default_rbac_seed(db, tenant_id=tenant_id)

    user_role_repo = UserRoleRepository(db)
    active_assignments = user_role_repo.get_active_assignments(user_id=user_id, tenant_id=tenant_id)
    if active_assignments:
        return active_assignments[0]

    roles = _list_all_roles_including_system(db)
    role_by_slug = {r.slug: r for r in roles}
    user_role = role_by_slug.get("user")
    if not user_role:
        raise HTTPException(status_code=500, detail="Default 'user' role missing")

    assignment = user_role_repo.assign_role(
        user_id=user_id,
        role_id=user_role.id,
        assigned_by=None,
        organization_id=None,
        organization_unit_id=None,
        expires_at=None,
    )
    db.commit()
    return assignment

