from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


EMBEDDING_DIMENSION = settings.PGVECTOR_EMBEDDING_DIMENSION


class AIMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_memories"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    importance_score: Mapped[float] = mapped_column(nullable=False, server_default="0.5")
    recency_score: Mapped[float] = mapped_column(nullable=False, server_default="1.0")
    decay_rate: Mapped[float] = mapped_column(nullable=False, server_default="0.001")
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="365")
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_ai_memories_tenant_type", "tenant_id", "memory_type"),
        Index("idx_ai_memories_tenant_source", "tenant_id", "source_type", "source_id"),
        Index("idx_ai_memories_tenant_created", "tenant_id", "created_at"),
    )


class MemoryChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memory_chunks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ai_memories.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False, server_default=str(EMBEDDING_DIMENSION))
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    keyword_vector: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_memory_chunks_tenant_memory", "tenant_id", "memory_id"),
        Index("idx_memory_chunks_tenant_created", "tenant_id", "created_at"),
        Index("idx_memory_chunks_chunk_hash", "chunk_hash"),
        Index(
            "idx_memory_chunks_embedding_ivfflat_cosine",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": settings.PGVECTOR_IVFFLAT_LISTS},
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class MemorySummary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memory_summaries"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ai_memories.id", ondelete="CASCADE"), nullable=False, index=True)
    summary_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="extractive")
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_memory_summaries_tenant_memory", "tenant_id", "memory_id"),
        Index("idx_memory_summaries_summary_hash", "summary_hash"),
    )


class MemoryRetrievalLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memory_retrieval_logs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    retrieval_mode: Mapped[str] = mapped_column(String(32), nullable=False, server_default="semantic")
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    __table_args__ = (
        Index("idx_memory_retrieval_logs_tenant_created", "tenant_id", "created_at"),
        Index("idx_memory_retrieval_logs_query_hash", "query_hash"),
    )


class ConversationContext(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversation_contexts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    context_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_budget: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1500")
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    context_version: Mapped[str] = mapped_column(String(32), nullable=False, server_default="v1")
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_conversation_contexts_tenant_conversation", "tenant_id", "conversation_id"),
        Index("idx_conversation_contexts_tenant_created", "tenant_id", "created_at"),
    )
