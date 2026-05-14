"""add ai memory persistence layer

Revision ID: 20260508_2100_add_ai_memory_persistence
Revises: 20260508_2000_add_auth_sessions
Create Date: 2026-05-08 21:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260508_2100_add_ai_memory_persistence'
down_revision = '20260508_2000_add_auth_sessions'
branch_labels = None
depends_on = None


def upgrade():
    # Create pgvector extension (idempotent)
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')

    # Create ai_conversations table
    op.create_table(
        'ai_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('conversation_type', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_ai_conversations_tenant_id', 'ai_conversations', ['tenant_id'])
    op.create_index('idx_ai_conversations_user_id', 'ai_conversations', ['user_id'])
    op.create_index('idx_ai_conversations_status', 'ai_conversations', ['status'])
    op.create_index('idx_ai_conversations_tenant_created_at', 'ai_conversations', ['tenant_id', 'created_at'])
    op.create_index('idx_ai_conversations_deleted_at', 'ai_conversations', ['deleted_at'])

    # Create ai_messages table
    op.create_table(
        'ai_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=128), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_ai_messages_tenant_conversation_recorded_at', 'ai_messages', ['tenant_id', 'conversation_id', 'recorded_at'])
    op.create_index('idx_ai_messages_content_hash', 'ai_messages', ['content_hash'])
    op.create_index('idx_ai_messages_role', 'ai_messages', ['role'])
    op.create_index('idx_ai_messages_deleted_at', 'ai_messages', ['deleted_at'])

    # Create ai_memory_summaries table
    op.create_table(
        'ai_memory_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_window_start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_window_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('summary_hash', sa.String(length=128), nullable=False),
        sa.Column('summary_version', sa.String(length=64), nullable=False, server_default='v1'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_ai_memory_summaries_tenant_conversation_end_at', 'ai_memory_summaries', ['tenant_id', 'conversation_id', 'source_window_end_at'])
    op.create_index('idx_ai_memory_summaries_summary_hash', 'ai_memory_summaries', ['summary_hash'])
    op.create_index('idx_ai_memory_summaries_deleted_at', 'ai_memory_summaries', ['deleted_at'])

    # Create ai_context_windows table
    op.create_table(
        'ai_context_windows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('window_start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('window_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('token_budget', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('selection_strategy', sa.String(length=64), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_ai_context_windows_tenant_conversation_end_at', 'ai_context_windows', ['tenant_id', 'conversation_id', 'window_end_at'])
    op.create_index('idx_ai_context_windows_deleted_at', 'ai_context_windows', ['deleted_at'])

    # Create ai_memory_chunks table
    op.create_table(
        'ai_memory_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_messages.id', ondelete='CASCADE'), nullable=True),
        sa.Column('summary_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_memory_summaries.id', ondelete='CASCADE'), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_hash', sa.String(length=128), nullable=False),
        sa.Column('chunk_type', sa.String(length=32), nullable=False, server_default='message'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('(message_id IS NOT NULL) OR (summary_id IS NOT NULL)', name='ck_ai_memory_chunks_source_present'),
        sa.CheckConstraint('NOT (message_id IS NOT NULL AND summary_id IS NOT NULL)', name='ck_ai_memory_chunks_source_exclusive'),
    )
    op.create_index('idx_ai_memory_chunks_tenant_conversation', 'ai_memory_chunks', ['tenant_id', 'conversation_id'])
    op.create_index('idx_ai_memory_chunks_chunk_hash', 'ai_memory_chunks', ['chunk_hash'])
    op.create_index('idx_ai_memory_chunks_created_at', 'ai_memory_chunks', ['tenant_id', 'created_at'])
    op.create_index('idx_ai_memory_chunks_deleted_at', 'ai_memory_chunks', ['deleted_at'])

    # Create ai_memory_embeddings table
    op.create_table(
        'ai_memory_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_memory_chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('embedding_model', sa.String(length=128), nullable=False),
        sa.Column('embedding_version', sa.String(length=64), nullable=False, server_default='v1'),
        sa.Column('embedding_dimension', sa.Integer(), nullable=False, server_default='1536'),
        sa.Column('content_hash', sa.String(length=128), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('embedded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('embedding', sa.Text(), nullable=False),  # Will be pgvector column via raw SQL
    )
    op.execute('ALTER TABLE ai_memory_embeddings ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536);')
    op.create_index('idx_ai_memory_embeddings_tenant_chunk', 'ai_memory_embeddings', ['tenant_id', 'chunk_id'])
    op.create_index('idx_ai_memory_embeddings_model_version', 'ai_memory_embeddings', ['tenant_id', 'embedding_model', 'embedding_version'])
    op.create_index('idx_ai_memory_embeddings_content_hash', 'ai_memory_embeddings', ['tenant_id', 'content_hash'])
    op.create_index('idx_ai_memory_embeddings_deleted_at', 'ai_memory_embeddings', ['deleted_at'])
    # Create vector index using ivfflat with cosine similarity
    op.execute('CREATE INDEX idx_ai_memory_embeddings_vector_cosine ON ai_memory_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);')

    # Create ai_memory_links table
    op.create_table(
        'ai_memory_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(length=64), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_type', sa.String(length=64), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relation_type', sa.String(length=64), nullable=False),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_ai_memory_links_source', 'ai_memory_links', ['tenant_id', 'source_type', 'source_id'])
    op.create_index('idx_ai_memory_links_target', 'ai_memory_links', ['tenant_id', 'target_type', 'target_id'])
    op.create_index('idx_ai_memory_links_relation', 'ai_memory_links', ['tenant_id', 'relation_type'])
    op.create_index('idx_ai_memory_links_deleted_at', 'ai_memory_links', ['deleted_at'])


def downgrade():
    # Drop tables in reverse dependency order
    op.drop_index('idx_ai_memory_links_deleted_at', table_name='ai_memory_links')
    op.drop_index('idx_ai_memory_links_relation', table_name='ai_memory_links')
    op.drop_index('idx_ai_memory_links_target', table_name='ai_memory_links')
    op.drop_index('idx_ai_memory_links_source', table_name='ai_memory_links')
    op.drop_table('ai_memory_links')

    op.drop_index('idx_ai_memory_embeddings_vector_cosine', table_name='ai_memory_embeddings')
    op.drop_index('idx_ai_memory_embeddings_deleted_at', table_name='ai_memory_embeddings')
    op.drop_index('idx_ai_memory_embeddings_content_hash', table_name='ai_memory_embeddings')
    op.drop_index('idx_ai_memory_embeddings_model_version', table_name='ai_memory_embeddings')
    op.drop_index('idx_ai_memory_embeddings_tenant_chunk', table_name='ai_memory_embeddings')
    op.drop_table('ai_memory_embeddings')

    op.drop_index('idx_ai_memory_chunks_deleted_at', table_name='ai_memory_chunks')
    op.drop_index('idx_ai_memory_chunks_created_at', table_name='ai_memory_chunks')
    op.drop_index('idx_ai_memory_chunks_chunk_hash', table_name='ai_memory_chunks')
    op.drop_index('idx_ai_memory_chunks_tenant_conversation', table_name='ai_memory_chunks')
    op.drop_table('ai_memory_chunks')

    op.drop_index('idx_ai_context_windows_deleted_at', table_name='ai_context_windows')
    op.drop_index('idx_ai_context_windows_tenant_conversation_end_at', table_name='ai_context_windows')
    op.drop_table('ai_context_windows')

    op.drop_index('idx_ai_memory_summaries_deleted_at', table_name='ai_memory_summaries')
    op.drop_index('idx_ai_memory_summaries_summary_hash', table_name='ai_memory_summaries')
    op.drop_index('idx_ai_memory_summaries_tenant_conversation_end_at', table_name='ai_memory_summaries')
    op.drop_table('ai_memory_summaries')

    op.drop_index('idx_ai_messages_deleted_at', table_name='ai_messages')
    op.drop_index('idx_ai_messages_role', table_name='ai_messages')
    op.drop_index('idx_ai_messages_content_hash', table_name='ai_messages')
    op.drop_index('idx_ai_messages_tenant_conversation_recorded_at', table_name='ai_messages')
    op.drop_table('ai_messages')

    op.drop_index('idx_ai_conversations_deleted_at', table_name='ai_conversations')
    op.drop_index('idx_ai_conversations_tenant_created_at', table_name='ai_conversations')
    op.drop_index('idx_ai_conversations_status', table_name='ai_conversations')
    op.drop_index('idx_ai_conversations_user_id', table_name='ai_conversations')
    op.drop_index('idx_ai_conversations_tenant_id', table_name='ai_conversations')
    op.drop_table('ai_conversations')

    # Drop pgvector extension (optional, keeping allows other future uses)
    # op.execute('DROP EXTENSION IF EXISTS vector;')
