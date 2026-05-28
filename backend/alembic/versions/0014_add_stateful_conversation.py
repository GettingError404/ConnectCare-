"""Add stateful conversation models and tables.

Revision ID: 0014_add_stateful_conversation
Revises: 0013_previous_migration
Create Date: 2026-05-26 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0014_add_stateful_conversation'
down_revision = '0013'  # Update to match your latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Conversation threads table
    op.create_table(
        'conversation_threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='active'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['user_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_conversation_threads_tenant', 'conversation_threads', ['tenant_id'])
    op.create_index('idx_conversation_threads_user', 'conversation_threads', ['user_id'])
    op.create_index('idx_conversation_threads_session', 'conversation_threads', ['session_id'])
    op.create_index('idx_conversation_threads_status', 'conversation_threads', ['status'])
    op.create_index('idx_conversation_threads_created', 'conversation_threads', ['created_at'])

    # Message acknowledgments table
    op.create_table(
        'message_acknowledgments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_sequence_no', sa.Integer(), nullable=False),
        sa.Column('last_chunk_sequence_no', sa.Integer(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversation_threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['user_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'message_sequence_no', name='uq_ack_session_message_seq')
    )
    op.create_index('idx_message_acks_conversation', 'message_acknowledgments', ['conversation_id'])
    op.create_index('idx_message_acks_session', 'message_acknowledgments', ['session_id'])

    # Streaming chunks table
    op.create_table(
        'streaming_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence_no', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('delta_tokens', sa.Integer(), nullable=True),
        sa.Column('persisted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['ai_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_streaming_chunks_message', 'streaming_chunks', ['message_id', 'chunk_index'])
    op.create_index('idx_streaming_chunks_sequence', 'streaming_chunks', ['sequence_no'])

    # Reconnect sessions table
    op.create_table(
        'reconnect_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('last_acked_message_sequence_no', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_acked_chunk_sequence_no', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pending_replay_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('resume_token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['user_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversation_threads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'conversation_id', name='uq_reconnect_session_conversation')
    )
    op.create_index('idx_reconnect_active', 'reconnect_sessions', 
                    ['session_id', 'conversation_id'],
                    postgresql_where=sa.text("resume_token_expires_at > NOW()"))

    # Context windows table
    op.create_table(
        'context_windows',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recent_message_count', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('total_tokens_in_window', sa.Integer(), nullable=False),
        sa.Column('truncated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('truncation_reason', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversation_threads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_context_windows_conversation', 'context_windows', ['conversation_id'])

    # Add columns to ai_messages table
    op.add_column('ai_messages', sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('ai_messages', sa.Column('sequence_no', sa.Integer(), nullable=True))
    op.add_column('ai_messages', sa.Column('parent_message_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('ai_messages', sa.Column('is_streaming', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('ai_messages', sa.Column('stream_complete', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('ai_messages', sa.Column('acknowledged_by_client', sa.Boolean(), nullable=False, server_default='false'))

    op.create_foreign_key(
        'fk_ai_messages_conversation',
        'ai_messages', 'conversation_threads',
        ['conversation_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_ai_messages_parent',
        'ai_messages', 'ai_messages',
        ['parent_message_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_ai_messages_recent', 'ai_messages', 
                    ['conversation_id', 'sequence_no'],
                    postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index('idx_ai_messages_sequence', 'ai_messages', ['sequence_no'])
    op.create_index('idx_ai_messages_streaming', 'ai_messages', 
                    ['is_streaming', 'stream_complete'])


def downgrade():
    # Drop columns from ai_messages
    op.drop_constraint('fk_ai_messages_conversation', 'ai_messages', type_='foreignkey')
    op.drop_constraint('fk_ai_messages_parent', 'ai_messages', type_='foreignkey')
    op.drop_index('idx_ai_messages_recent')
    op.drop_index('idx_ai_messages_sequence')
    op.drop_index('idx_ai_messages_streaming')
    op.drop_column('ai_messages', 'acknowledged_by_client')
    op.drop_column('ai_messages', 'stream_complete')
    op.drop_column('ai_messages', 'is_streaming')
    op.drop_column('ai_messages', 'parent_message_id')
    op.drop_column('ai_messages', 'sequence_no')
    op.drop_column('ai_messages', 'conversation_id')

    # Drop new tables
    op.drop_table('context_windows')
    op.drop_table('reconnect_sessions')
    op.drop_table('streaming_chunks')
    op.drop_table('message_acknowledgments')
    op.drop_table('conversation_threads')
