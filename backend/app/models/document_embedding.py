from __future__ import annotations

from sqlalchemy import Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.core.config import settings
from app.models.vector_base import TenantVectorBase


EMBEDDING_DIMENSION = settings.PGVECTOR_EMBEDDING_DIMENSION
IVFFLAT_LISTS = settings.PGVECTOR_IVFFLAT_LISTS


class DocumentEmbedding(TenantVectorBase):
    """Example vector-enabled model for semantic document retrieval."""

    __tablename__ = "document_embeddings"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False, server_default="example-embedding-v1")
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False, server_default=str(EMBEDDING_DIMENSION))
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)

    __table_args__ = (
        Index("idx_document_embeddings_tenant_source", "tenant_id", "source_type", "source_id"),
        Index("idx_document_embeddings_tenant_created_at", "tenant_id", "created_at"),
        Index("idx_document_embeddings_tenant_content_hash", "tenant_id", "content_hash"),
        Index(
            "idx_document_embeddings_embedding_ivfflat_cosine",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": IVFFLAT_LISTS},
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
