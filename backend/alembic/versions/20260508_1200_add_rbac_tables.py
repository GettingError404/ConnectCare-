"""Add RBAC tables

Revision ID: 20260508_1200_rbac
Revises: 20260508_1130_users_tenant
Create Date: 2026-05-08 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260508_1200_rbac"
down_revision = "20260508_1130_users_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("resource", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
    )
    op.create_index("idx_permissions_resource_action", "permissions", ["resource", "action"])

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_role_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_role_id"], ["roles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_roles_tenant_slug"),
    )
    op.create_index("idx_roles_tenant_id", "roles", ["tenant_id"])
    op.create_index("idx_roles_tenant_slug", "roles", ["tenant_id", "slug"])
    op.create_index("idx_roles_parent_role_id", "roles", ["parent_role_id"])
    op.create_index("idx_roles_is_active", "roles", ["is_active"])
    op.create_index("idx_roles_deleted_at", "roles", ["deleted_at"])

    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_unit_id"], ["organization_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("idx_user_roles_role_id", "user_roles", ["role_id"])
    op.create_index("idx_user_roles_organization_id", "user_roles", ["organization_id"])
    op.create_index("idx_user_roles_organization_unit_id", "user_roles", ["organization_unit_id"])
    op.create_index("idx_user_roles_is_active", "user_roles", ["is_active"])
    op.create_index("idx_user_roles_expires_at", "user_roles", ["expires_at"])
    op.create_index("idx_user_roles_user_scope", "user_roles", ["user_id", "organization_id", "organization_unit_id"])


def downgrade() -> None:
    op.drop_index("idx_user_roles_user_scope", table_name="user_roles")
    op.drop_index("idx_user_roles_expires_at", table_name="user_roles")
    op.drop_index("idx_user_roles_is_active", table_name="user_roles")
    op.drop_index("idx_user_roles_organization_unit_id", table_name="user_roles")
    op.drop_index("idx_user_roles_organization_id", table_name="user_roles")
    op.drop_index("idx_user_roles_role_id", table_name="user_roles")
    op.drop_index("idx_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_table("role_permissions")

    op.drop_index("idx_roles_deleted_at", table_name="roles")
    op.drop_index("idx_roles_is_active", table_name="roles")
    op.drop_index("idx_roles_parent_role_id", table_name="roles")
    op.drop_index("idx_roles_tenant_slug", table_name="roles")
    op.drop_index("idx_roles_tenant_id", table_name="roles")
    op.drop_table("roles")

    op.drop_index("idx_permissions_resource_action", table_name="permissions")
    op.drop_table("permissions")
