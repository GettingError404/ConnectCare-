"""add auth sessions and refresh tokens

Revision ID: 20260508_2000_add_auth_sessions
Revises: 20260508_1330_add_alerts
Create Date: 2026-05-08 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260508_2000_add_auth_sessions'
down_revision = '20260508_1330_add_alerts'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('device_info', sa.String(length=512), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=1024), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_user_sessions_tenant_id', 'user_sessions', ['tenant_id'])
    op.create_index('idx_user_sessions_tenant_user_id', 'user_sessions', ['tenant_id', 'user_id'])

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('jti', sa.String(length=128), nullable=False, unique=True),
        sa.Column('family_id', sa.String(length=128), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('replaced_by', sa.String(length=128), nullable=True),
    )
    op.create_index('idx_refresh_tokens_jti', 'refresh_tokens', ['jti'])
    op.create_index('idx_refresh_tokens_family', 'refresh_tokens', ['family_id'])
    op.create_index('idx_refresh_tokens_user', 'refresh_tokens', ['user_id'])
    op.create_index('idx_refresh_tokens_session', 'refresh_tokens', ['session_id'])


def downgrade():
    # drop indexes and tables idempotently
    op.drop_index('idx_refresh_tokens_session', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_user', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_family', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_jti', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')

    op.drop_index('idx_user_sessions_tenant_user_id', table_name='user_sessions')
    op.drop_index('idx_user_sessions_tenant_id', table_name='user_sessions')
    op.drop_index('idx_user_sessions_user_id', table_name='user_sessions')
    op.drop_table('user_sessions')
