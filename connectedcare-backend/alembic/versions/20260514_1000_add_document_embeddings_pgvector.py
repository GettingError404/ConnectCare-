"""add document embeddings with pgvector

Revision ID: 20260514_1000_add_document_embeddings_pgvector
Revises: 20260508_2100_add_ai_memory_persistence
Create Date: 2026-05-14 10:00:00.000000
"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260514_1000_add_document_embeddings_pgvector"
down_revision = "20260508_2100_add_ai_memory_persistence"
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
        "document_embeddings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False, server_default="example-embedding-v1"),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False, server_default=str(dimension)),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding", Vector(dimension), nullable=False),
    )

    op.create_index(
        "idx_document_embeddings_tenant_source",
        "document_embeddings",
        ["tenant_id", "source_type", "source_id"],
    )
    op.create_index(
        "idx_document_embeddings_tenant_created_at",
        "document_embeddings",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_document_embeddings_tenant_content_hash",
        "document_embeddings",
        ["tenant_id", "content_hash"],
    )
    op.create_index(
        "idx_document_embeddings_deleted_at",
        "document_embeddings",
        ["deleted_at"],
    )

    op.create_index(
        "idx_document_embeddings_embedding_ivfflat_cosine",
        "document_embeddings",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_with={"lists": lists},
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_document_embeddings_embedding_ivfflat_cosine", table_name="document_embeddings")
    op.drop_index("idx_document_embeddings_deleted_at", table_name="document_embeddings")
    op.drop_index("idx_document_embeddings_tenant_content_hash", table_name="document_embeddings")
    op.drop_index("idx_document_embeddings_tenant_created_at", table_name="document_embeddings")
    op.drop_index("idx_document_embeddings_tenant_source", table_name="document_embeddings")
    op.drop_table("document_embeddings")
