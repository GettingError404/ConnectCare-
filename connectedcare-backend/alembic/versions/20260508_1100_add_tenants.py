"""Add tenants, organizations, and organization_units tables

Revision ID: 20260508_1100_tenants
Revises: 20260506a2
Create Date: 2026-05-08 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260508_1100_tenants'
down_revision = '20260506a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.create_index('idx_tenants_slug', 'tenants', ['slug'])
    op.create_index('idx_tenants_is_active', 'tenants', ['is_active'])
    op.create_index('idx_tenants_deleted_at', 'tenants', ['deleted_at'])

    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_organizations_tenant_id', 'organizations', ['tenant_id'])
    op.create_index('idx_organizations_tenant_slug', 'organizations', ['tenant_id', 'slug'])
    op.create_index('idx_organizations_is_active', 'organizations', ['is_active'])
    op.create_index('idx_organizations_deleted_at', 'organizations', ['deleted_at'])

    # Create organization_units table
    op.create_table(
        'organization_units',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['organization_units.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_org_units_organization_id', 'organization_units', ['organization_id'])
    op.create_index('idx_org_units_parent_id', 'organization_units', ['parent_id'])
    op.create_index('idx_org_units_org_parent', 'organization_units', ['organization_id', 'parent_id'])
    op.create_index('idx_org_units_is_active', 'organization_units', ['is_active'])
    op.create_index('idx_org_units_deleted_at', 'organization_units', ['deleted_at'])


def downgrade() -> None:
    # Drop organization_units table
    op.drop_index('idx_org_units_deleted_at', 'organization_units')
    op.drop_index('idx_org_units_is_active', 'organization_units')
    op.drop_index('idx_org_units_org_parent', 'organization_units')
    op.drop_index('idx_org_units_parent_id', 'organization_units')
    op.drop_index('idx_org_units_organization_id', 'organization_units')
    op.drop_table('organization_units')

    # Drop organizations table
    op.drop_index('idx_organizations_deleted_at', 'organizations')
    op.drop_index('idx_organizations_is_active', 'organizations')
    op.drop_index('idx_organizations_tenant_slug', 'organizations')
    op.drop_index('idx_organizations_tenant_id', 'organizations')
    op.drop_table('organizations')

    # Drop tenants table
    op.drop_index('idx_tenants_deleted_at', 'tenants')
    op.drop_index('idx_tenants_is_active', 'tenants')
    op.drop_index('idx_tenants_slug', 'tenants')
    op.drop_table('tenants')
