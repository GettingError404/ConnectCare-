"""add ai memory intelligence layer

Revision ID: 20260514_1600_add_ai_memory_intelligence_layer
Revises: 20260514_1000_add_document_embeddings_pgvector
Create Date: 2026-05-14 16:00:00.000000
"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision = "20260514_1600_add_ai_memory_intelligence_layer"
down_revision = "20260514_1000_add_document_embeddings_pgvector"
branch_labels = None
depends_on = None


def _embedding_dimension() -> int:
    return int(os.getenv("PGVECTOR_EMBEDDING_DIMENSION", "1536"))


def _ivfflat_lists() -> int:
    return int(os.getenv("PGVECTOR_IVFFLAT_LISTS", "100"))


def upgrade() -> None:
    dimension = _embedding_dimension()
    lists = _ivfflat_lists()

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "ai_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("memory_type", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("recency_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("decay_rate", sa.Float(), nullable=False, server_default="0.001"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_ai_memories_tenant_type", "ai_memories", ["tenant_id", "memory_type"])
    op.create_index("idx_ai_memories_tenant_source", "ai_memories", ["tenant_id", "source_type", "source_id"])
    op.create_index("idx_ai_memories_tenant_created", "ai_memories", ["tenant_id", "created_at"])

    op.create_table(
        "memory_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_memories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_hash", sa.String(length=128), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False, server_default=str(dimension)),
        sa.Column("embedding", Vector(dimension), nullable=False),
        sa.Column("keyword_vector", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_memory_chunks_tenant_memory", "memory_chunks", ["tenant_id", "memory_id"])
    op.create_index("idx_memory_chunks_tenant_created", "memory_chunks", ["tenant_id", "created_at"])
    op.create_index("idx_memory_chunks_chunk_hash", "memory_chunks", ["chunk_hash"])
    op.create_index(
        "idx_memory_chunks_embedding_ivfflat_cosine",
        "memory_chunks",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_with={"lists": lists},
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "memory_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_memories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary_type", sa.String(length=32), nullable=False, server_default="extractive"),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("summary_hash", sa.String(length=128), nullable=False),
        sa.Column("source_chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_memory_summaries_tenant_memory", "memory_summaries", ["tenant_id", "memory_id"])
    op.create_index("idx_memory_summaries_summary_hash", "memory_summaries", ["summary_hash"])

    op.create_table(
        "memory_retrieval_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("query_hash", sa.String(length=128), nullable=False),
        sa.Column("retrieval_mode", sa.String(length=32), nullable=False, server_default="semantic"),
        sa.Column("top_k", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("idx_memory_retrieval_logs_tenant_created", "memory_retrieval_logs", ["tenant_id", "created_at"])
    op.create_index("idx_memory_retrieval_logs_query_hash", "memory_retrieval_logs", ["query_hash"])

    op.create_table(
        "conversation_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("context_text", sa.Text(), nullable=False),
        sa.Column("token_budget", sa.Integer(), nullable=False, server_default="1500"),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("context_version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_conversation_contexts_tenant_conversation", "conversation_contexts", ["tenant_id", "conversation_id"])
    op.create_index("idx_conversation_contexts_tenant_created", "conversation_contexts", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_conversation_contexts_tenant_created", table_name="conversation_contexts")
    op.drop_index("idx_conversation_contexts_tenant_conversation", table_name="conversation_contexts")
    op.drop_table("conversation_contexts")

    op.drop_index("idx_memory_retrieval_logs_query_hash", table_name="memory_retrieval_logs")
    op.drop_index("idx_memory_retrieval_logs_tenant_created", table_name="memory_retrieval_logs")
    op.drop_table("memory_retrieval_logs")

    op.drop_index("idx_memory_summaries_summary_hash", table_name="memory_summaries")
    op.drop_index("idx_memory_summaries_tenant_memory", table_name="memory_summaries")
    op.drop_table("memory_summaries")

    op.drop_index("idx_memory_chunks_embedding_ivfflat_cosine", table_name="memory_chunks")
    op.drop_index("idx_memory_chunks_chunk_hash", table_name="memory_chunks")
    op.drop_index("idx_memory_chunks_tenant_created", table_name="memory_chunks")
    op.drop_index("idx_memory_chunks_tenant_memory", table_name="memory_chunks")
    op.drop_table("memory_chunks")

    op.drop_index("idx_ai_memories_tenant_created", table_name="ai_memories")
    op.drop_index("idx_ai_memories_tenant_source", table_name="ai_memories")
    op.drop_index("idx_ai_memories_tenant_type", table_name="ai_memories")
    op.drop_table("ai_memories")
