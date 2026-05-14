"""Add tenant_id to users table

Revision ID: 20260508_1130_users_tenant
Revises: 20260508_1100_tenants
Create Date: 2026-05-08 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260508_1130_users_tenant'
down_revision = '20260508_1100_tenants'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tenant_id column to users
    op.add_column(
        'users',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_users_tenant_id',
        'users', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Add index
    op.create_index('idx_users_tenant_id', 'users', ['tenant_id'])


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_users_tenant_id', 'users')
    
    # Remove foreign key constraint
    op.drop_constraint('fk_users_tenant_id', 'users', type_='foreignkey')
    
    # Remove column
    op.drop_column('users', 'tenant_id')
