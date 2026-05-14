from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AudioSessionCreateRequest(BaseModel):
    conversation_id: UUID | None = None
    language: str | None = Field(default=None, max_length=16)
    source_language: str | None = Field(default=None, max_length=16)
    target_language: str | None = Field(default=None, max_length=16)
    metadata: dict | None = None


class AudioSessionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID | None = None
    conversation_id: UUID | None = None
    status: str
    language: str | None = None
    source_language: str | None = None
    target_language: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AudioUploadRequest(BaseModel):
    sequence_no: int = Field(ge=0)
    chunk_index: int = Field(ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    mime_type: str | None = Field(default=None, max_length=64)
    audio_base64: str = Field(min_length=1)
    metadata: dict | None = None


class AudioUploadResponse(BaseModel):
    session_id: UUID
    chunk_id: UUID
    sequence_no: int


class TranscriptionRequest(BaseModel):
    text: str | None = None
    audio_base64: str | None = None
    sequence_no: int | None = Field(default=None, ge=0)
    is_partial: bool = False
    language: str | None = None


class TranscriptionResponse(BaseModel):
    stt_result_id: UUID
    transcript: str
    confidence: float | None = None
    detected_language: str | None = None
    is_partial: bool


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1)
    source_language: str | None = None
    target_language: str = Field(min_length=2, max_length=16)


class TranslationResponse(BaseModel):
    translation_id: UUID
    source_language: str
    target_language: str
    translated_text: str
    confidence: float | None = None


class NLPRequest(BaseModel):
    text: str = Field(min_length=1)
    conversation_id: UUID | None = None


class NLPResponse(BaseModel):
    nlp_result_id: UUID
    intent: str | None = None
    entities: dict | None = None
    sentiment: str | None = None
    confidence: float | None = None
    healthcare_flags: dict | None = None


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    language: str | None = None
    voice: str | None = None


class TTSResponse(BaseModel):
    tts_output_id: UUID
    voice: str | None = None
    language: str | None = None
    audio_base64: str


class RealtimeConversationRequest(BaseModel):
    user_text: str = Field(min_length=1)
    top_k: int = Field(default=8, ge=1, le=50)


class RealtimeConversationResponse(BaseModel):
    ai_response_id: UUID
    response_text: str
    context_preview: str | None = None


class VoiceEventResponse(BaseModel):
    event_id: UUID
    session_id: UUID
    sequence_no: int
    event_type: str
    event_payload: dict
    sent_at: datetime | None = None


class ConversationHistoryResponse(BaseModel):
    session_id: UUID
    stt_results: list[dict]
    translations: list[dict]
    nlp_results: list[dict]
    ai_responses: list[dict]


class VoiceAnalyticsResponse(BaseModel):
    total_sessions: int
    total_audio_chunks: int
    total_stt_results: int
    total_translations: int
    total_nlp_results: int
    total_tts_outputs: int
    total_ai_responses: int
    avg_response_latency_ms: float
