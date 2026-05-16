"""Seed RBAC permissions and system roles

Revision ID: 20260508_1210_rbac_seed
Revises: 20260508_1200_rbac
Create Date: 2026-05-08 12:10:00.000000
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260508_1210_rbac_seed"
down_revision = "20260508_1200_rbac"
branch_labels = None
depends_on = None


def stable_uuid(value: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"connectedcare-rbac:{value}")


def upgrade() -> None:
    permissions = [
        ("users", "create", "Create users"),
        ("users", "view", "View users"),
        ("users", "update", "Update users"),
        ("users", "delete", "Delete users"),
        ("vitals", "view", "View vitals"),
        ("vitals", "create", "Create vitals"),
        ("alerts", "view", "View alerts"),
        ("alerts", "manage", "Manage alerts"),
        ("devices", "register", "Register devices"),
        ("organizations", "manage", "Manage organizations"),
        ("tenants", "manage", "Manage tenants"),
        ("elders", "view", "View elders"),
        ("elders", "create", "Create elders"),
        ("elders", "update", "Update elders"),
        ("elders", "delete", "Delete elders"),
        ("careplans", "manage", "Manage care plans"),
        ("medical", "read", "Read medical profiles"),
        ("medical", "update", "Update medical profiles"),
        ("roles", "view", "View roles"),
        ("roles", "manage", "Manage roles"),
        ("permissions", "view", "View permissions"),
        ("user_roles", "manage", "Manage user roles"),
    ]
    permission_rows = [
        {
            "id": stable_uuid(f"permission:{resource}:{action}"),
            "resource": resource,
            "action": action,
            "description": description,
        }
        for resource, action, description in permissions
    ]
    op.bulk_insert(
        sa.table(
            "permissions",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("resource", sa.String()),
            sa.column("action", sa.String()),
            sa.column("description", sa.Text()),
        ),
        permission_rows,
    )

    roles = [
        ("super_admin", "Super Administrator", "Full access across tenants", None, True),
        ("tenant_admin", "Tenant Administrator", "Tenant-level administrator", "super_admin", True),
        ("doctor", "Doctor", "Clinical access", "tenant_admin", True),
        ("nurse", "Nurse", "Nursing access", "tenant_admin", True),
        ("caregiver", "Caregiver", "Caregiver access", "tenant_admin", True),
        ("family_member", "Family Member", "Family access", "tenant_admin", True),
        ("elder", "Elder", "Elder access", "tenant_admin", True),
    ]
    role_lookup = {slug: stable_uuid(f"role:{slug}") for slug, *_ in roles}
    role_rows = []
    for slug, name, description, parent_slug, is_system_role in roles:
        role_rows.append(
            {
                "id": role_lookup[slug],
                "tenant_id": None,
                "parent_role_id": role_lookup.get(parent_slug) if parent_slug else None,
                "name": name,
                "slug": slug,
                "description": description,
                "is_system_role": is_system_role,
                "is_active": True,
            }
        )

    op.bulk_insert(
        sa.table(
            "roles",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
            sa.column("parent_role_id", postgresql.UUID(as_uuid=True)),
            sa.column("name", sa.String()),
            sa.column("slug", sa.String()),
            sa.column("description", sa.Text()),
            sa.column("is_system_role", sa.Boolean()),
            sa.column("is_active", sa.Boolean()),
        ),
        role_rows,
    )

    permission_lookup = {f"{resource}:{action}": stable_uuid(f"permission:{resource}:{action}") for resource, action, _ in permissions}
    role_permission_map = {
        "super_admin": list(permission_lookup.keys()),
        "tenant_admin": [
            "users:create",
            "users:view",
            "users:update",
            "users:delete",
            "vitals:view",
            "vitals:create",
            "alerts:view",
            "alerts:manage",
            "devices:register",
            "organizations:manage",
            "roles:view",
            "roles:manage",
            "permissions:view",
            "user_roles:manage",
            "elders:view",
            "elders:create",
            "elders:update",
            "elders:delete",
            "careplans:manage",
            "medical:read",
            "medical:update",
        ],
        "doctor": ["vitals:view", "vitals:create", "alerts:view", "medical:read", "medical:update", "elders:view"],
        "nurse": ["vitals:view", "vitals:create", "alerts:view", "alerts:manage", "medical:read"],
        "caregiver": ["vitals:view", "alerts:view", "devices:register", "elders:view"],
        "family_member": ["vitals:view", "alerts:view", "elders:view"],
        "elder": ["vitals:view", "elders:view"],
    }

    role_permission_rows = []
    for role_slug, permission_keys in role_permission_map.items():
        for permission_key in permission_keys:
            role_permission_rows.append(
                {
                    "role_id": role_lookup[role_slug],
                    "permission_id": permission_lookup[permission_key],
                }
            )

    op.bulk_insert(
        sa.table(
            "role_permissions",
            sa.column("role_id", postgresql.UUID(as_uuid=True)),
            sa.column("permission_id", postgresql.UUID(as_uuid=True)),
        ),
        role_permission_rows,
    )


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions")
    op.execute("DELETE FROM roles")
    op.execute("DELETE FROM permissions")
