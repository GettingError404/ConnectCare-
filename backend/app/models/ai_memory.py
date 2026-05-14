from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover - import resolution depends on installed dependency
    Vector = None  # type: ignore[assignment]

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


# Keep the dimension explicit so the schema, embeddings, and future reindex jobs agree.
EMBEDDING_DIMENSION = 1536


class AIConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_conversations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    conversation_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, name="metadata")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        # Soft delete preserves auditability without hard deletion during retention workflows.
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[Optional["User"]] = relationship(lazy="selectin")
    messages: Mapped[list["AIMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        foreign_keys="AIMessage.conversation_id",
        lazy="selectin",
    )
    summaries: Mapped[list["AIMemorySummary"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        foreign_keys="AIMemorySummary.conversation_id",
        lazy="selectin",
    )
    context_windows: Mapped[list["AIContextWindow"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        foreign_keys="AIContextWindow.conversation_id",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_ai_conversations_tenant_id", "tenant_id"),
        Index("idx_ai_conversations_user_id", "user_id"),
        Index("idx_ai_conversations_status", "status"),
        Index("idx_ai_conversations_tenant_created_at", "tenant_id", "created_at"),
        Index("idx_ai_conversations_deleted_at", "deleted_at"),
    )


class AIMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_messages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    token_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    recorded_at: Mapped[Optional[datetime]] = mapped_column(
        # Keep an explicit time-axis field for future TimescaleDB alignment and audit replay.
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, name="metadata")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    conversation: Mapped["AIConversation"] = relationship(back_populates="messages")
    chunks: Mapped[list["AIMemoryChunk"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        foreign_keys="AIMemoryChunk.message_id",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_ai_messages_tenant_conversation_recorded_at", "tenant_id", "conversation_id", "recorded_at"),
        Index("idx_ai_messages_content_hash", "content_hash"),
        Index("idx_ai_messages_role", "role"),
        Index("idx_ai_messages_deleted_at", "deleted_at"),
    )


class AIMemorySummary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_memory_summaries"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_window_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_window_end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    summary_version: Mapped[str] = mapped_column(String(64), nullable=False, server_default="v1")
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, name="metadata")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    conversation: Mapped["AIConversation"] = relationship(back_populates="summaries")
    chunks: Mapped[list["AIMemoryChunk"]] = relationship(
        back_populates="summary",
        foreign_keys="AIMemoryChunk.summary_id",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_ai_memory_summaries_tenant_conversation_end_at", "tenant_id", "conversation_id", "source_window_end_at"),
        Index("idx_ai_memory_summaries_summary_hash", "summary_hash"),
        Index("idx_ai_memory_summaries_deleted_at", "deleted_at"),
    )


class AIContextWindow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_context_windows"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    window_start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    window_end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    token_budget: Mapped[Optional[int]] = mapped_column(nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(nullable=True)
    selection_strategy: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, name="metadata")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    conversation: Mapped["AIConversation"] = relationship(back_populates="context_windows")

    __table_args__ = (
        Index("idx_ai_context_windows_tenant_conversation_end_at", "tenant_id", "conversation_id", "window_end_at"),
        Index("idx_ai_context_windows_deleted_at", "deleted_at"),
    )


class AIMemoryChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_memory_chunks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_messages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    summary_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_memory_summaries.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    chunk_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="message")
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, name="metadata")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    conversation: Mapped["AIConversation"] = relationship(lazy="selectin")
    message: Mapped[Optional["AIMessage"]] = relationship(back_populates="chunks")
    summary: Mapped[Optional["AIMemorySummary"]] = relationship(back_populates="chunks")
    embeddings: Mapped[list["AIMemoryEmbedding"]] = relationship(
        back_populates="chunk",
        cascade="all, delete-orphan",
        foreign_keys="AIMemoryEmbedding.chunk_id",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_ai_memory_chunks_tenant_conversation", "tenant_id", "conversation_id"),
        Index("idx_ai_memory_chunks_chunk_hash", "chunk_hash"),
        Index("idx_ai_memory_chunks_created_at", "tenant_id", "created_at"),
        Index("idx_ai_memory_chunks_deleted_at", "deleted_at"),
        CheckConstraint(
            "(message_id IS NOT NULL) OR (summary_id IS NOT NULL)",
            name="ck_ai_memory_chunks_source_present",
        ),
        CheckConstraint(
            "NOT (message_id IS NOT NULL AND summary_id IS NOT NULL)",
            name="ck_ai_memory_chunks_source_exclusive",
        ),
    )


class AIMemoryEmbedding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_memory_embeddings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_memory_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(64), nullable=False, server_default="v1")
    embedding_dimension: Mapped[int] = mapped_column(nullable=False, server_default=str(EMBEDDING_DIMENSION))
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, name="metadata")
    embedded_at: Mapped[Optional[datetime]] = mapped_column(
        # Audit-friendly timestamp for re-embedding and freshness checks.
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    chunk: Mapped["AIMemoryChunk"] = relationship(back_populates="embeddings")

    if Vector is not None:
        embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    else:  # pragma: no cover - import resolution depends on installed dependency
        embedding = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_ai_memory_embeddings_tenant_chunk", "tenant_id", "chunk_id"),
        Index("idx_ai_memory_embeddings_model_version", "tenant_id", "embedding_model", "embedding_version"),
        Index("idx_ai_memory_embeddings_content_hash", "tenant_id", "content_hash"),
        Index("idx_ai_memory_embeddings_deleted_at", "deleted_at"),
        Index(
            "idx_ai_memory_embeddings_vector_cosine",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class AIMemoryLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_memory_links"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    weight: Mapped[Optional[float]] = mapped_column(nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, name="metadata")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_ai_memory_links_source", "tenant_id", "source_type", "source_id"),
        Index("idx_ai_memory_links_target", "tenant_id", "target_type", "target_id"),
        Index("idx_ai_memory_links_relation", "tenant_id", "relation_type"),
        Index("idx_ai_memory_links_deleted_at", "deleted_at"),
    )
