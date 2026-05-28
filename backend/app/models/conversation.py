"""SQLAlchemy models for stateful conversation system.

Models:
- ConversationThread: represents a single conversation thread
- MessageAcknowledgment: tracks client acknowledgments
- StreamingChunk: incremental message chunks
- ReconnectSession: reconnect/replay state
- ContextWindow: context metadata
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.auth import UserSession
    from app.models.ai_memory import AIMessage


class ConversationThread(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Represents a single conversation thread within a session.
    
    A session may have multiple conversation threads (e.g., user switches
    between topics or restarts the conversation). Each thread groups
    related messages.
    """
    __tablename__ = "conversation_threads"

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
    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="active",
        index=True,
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        name="metadata",
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[Optional["User"]] = relationship(lazy="selectin")
    session: Mapped["UserSession"] = relationship(lazy="selectin")

    messages: Mapped[list["AIMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        foreign_keys="AIMessage.conversation_id",
    )

    acknowledgments: Mapped[list["MessageAcknowledgment"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        foreign_keys="MessageAcknowledgment.conversation_id",
    )

    reconnect_sessions: Mapped[list["ReconnectSession"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        foreign_keys="ReconnectSession.conversation_id",
    )

    context_windows: Mapped[list["ContextWindow"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        foreign_keys="ContextWindow.conversation_id",
    )

    __table_args__ = (
        Index("idx_conversation_threads_created", "created_at"),
    )


class MessageAcknowledgment(UUIDPrimaryKeyMixin, Base):
    """Tracks client acknowledgment of streamed messages.
    
    When a client receives message chunks, it sends acknowledgments
    to confirm receipt. This allows the server to track which chunks
    need replay on reconnect.
    """
    __tablename__ = "message_acknowledgments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversation_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    last_chunk_sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=lambda: datetime.utcnow(),
    )

    conversation: Mapped["ConversationThread"] = relationship(back_populates="acknowledgments")

    __table_args__ = (
        Index("idx_message_acks_session", "session_id"),
        Index("uq_ack_session_message_seq", "session_id", "message_sequence_no", unique=True),
    )


class StreamingChunk(UUIDPrimaryKeyMixin, Base):
    """Represents a single chunk of a streamed message.
    
    When an AI agent streams a response in chunks, each chunk is
    persisted here for:
    - Replay on client reconnect
    - Audit trail
    - Analytics (chunk timing, token count)
    """
    __tablename__ = "streaming_chunks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    delta_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    persisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=lambda: datetime.utcnow(),
    )

    __table_args__ = (
        Index("idx_streaming_chunks_message", "message_id", "chunk_index"),
    )


class ReconnectSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks session state for reconnect/replay scenarios.
    
    When a client reconnects, this table allows the server to:
    - Identify unacknowledged messages
    - Determine which chunks to replay
    - Resume streaming from the correct position
    """
    __tablename__ = "reconnect_sessions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversation_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_acked_message_sequence_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    last_acked_chunk_sequence_no: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    pending_replay_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        server_default="0",
    )
    resume_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    conversation: Mapped["ConversationThread"] = relationship(back_populates="reconnect_sessions")

    __table_args__ = (
        Index(
            "uq_reconnect_session_conversation",
            "session_id",
            "conversation_id",
            unique=True,
        ),
    )


class ContextWindow(UUIDPrimaryKeyMixin, Base):
    """Metadata about context built for a message.
    
    After building context for a message (recent history + semantic
    memories + summaries), this record tracks:
    - How many messages were included
    - Total token count
    - Whether truncation occurred
    - Why truncation happened (if applicable)
    """
    __tablename__ = "context_windows"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversation_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recent_message_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="5",
    )
    total_tokens_in_window: Mapped[int] = mapped_column(Integer, nullable=False)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    truncation_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=lambda: datetime.utcnow(),
    )

    conversation: Mapped["ConversationThread"] = relationship(back_populates="context_windows")
