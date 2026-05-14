from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AudioSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audio_sessions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active", index=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_audio_sessions_tenant_status", "tenant_id", "status"),
        Index("idx_audio_sessions_tenant_conversation", "tenant_id", "conversation_id"),
    )


class AudioChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audio_chunks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audio_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audio_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    blob_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    __table_args__ = (
        Index("idx_audio_chunks_tenant_session_seq", "tenant_id", "session_id", "sequence_no"),
    )


class STTResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stt_results"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audio_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audio_chunks.id", ondelete="CASCADE"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    is_partial: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)


class Translation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "translations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audio_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    stt_result_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stt_results.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    source_language: Mapped[str] = mapped_column(String(16), nullable=False)
    target_language: Mapped[str] = mapped_column(String(16), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)


class NLPResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nlp_results"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audio_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    stt_result_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stt_results.id", ondelete="SET NULL"), nullable=True, index=True)
    translation_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("translations.id", ondelete="SET NULL"), nullable=True, index=True)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    healthcare_flags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)


class TTSOutput(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tts_outputs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audio_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    voice: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    text_input: Mapped[str] = mapped_column(Text, nullable=False)
    audio_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)


class AIVoiceResponse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_voice_responses"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audio_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    stt_result_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stt_results.id", ondelete="SET NULL"), nullable=True, index=True)
    translation_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("translations.id", ondelete="SET NULL"), nullable=True, index=True)
    nlp_result_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("nlp_results.id", ondelete="SET NULL"), nullable=True, index=True)
    tts_output_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tts_outputs.id", ondelete="SET NULL"), nullable=True, index=True)
    prompt_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)


class RealtimeVoiceEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "realtime_voice_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("audio_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_realtime_voice_events_tenant_session_seq", "tenant_id", "session_id", "sequence_no"),
        Index("idx_realtime_voice_events_type", "event_type"),
    )
