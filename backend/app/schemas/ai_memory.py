from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryIngestBase(BaseModel):
    source_id: UUID | None = None
    title: str | None = Field(default=None, max_length=255)
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    metadata: dict | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)


class ConversationMemoryIngestRequest(MemoryIngestBase):
    conversation_id: UUID


class DocumentMemoryIngestRequest(MemoryIngestBase):
    document_id: UUID


class ClinicalNoteMemoryIngestRequest(MemoryIngestBase):
    patient_id: UUID | None = None
    note_id: UUID | None = None


class IngestedMemoryChunk(BaseModel):
    id: UUID
    chunk_index: int
    token_count: int


class MemoryIngestResponse(BaseModel):
    memory_id: UUID
    chunk_count: int
    chunks: list[IngestedMemoryChunk]


class MemoryRetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    memory_types: list[str] | None = None
    source_types: list[str] | None = None
    metadata_filter: dict | None = None
    conversation_id: UUID | None = None
    use_hybrid_search: bool = True
    recency_boost_weight: float = Field(default=0.15, ge=0.0, le=1.0)


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    metadata_filter: dict | None = None


class RetrievedMemoryItem(BaseModel):
    memory_id: UUID
    chunk_id: UUID
    content: str
    memory_type: str
    source_type: str
    semantic_score: float
    hybrid_score: float
    recency_score: float
    final_score: float
    created_at: datetime
    metadata: dict | None = None


class MemoryRetrieveResponse(BaseModel):
    results: list[RetrievedMemoryItem]
    retrieval_mode: str
    total_results: int


class GenerateContextRequest(BaseModel):
    conversation_id: UUID
    user_query: str = Field(min_length=1)
    token_budget: int = Field(default=1500, ge=256, le=16000)
    top_k: int = Field(default=10, ge=1, le=50)


class GenerateContextResponse(BaseModel):
    context_id: UUID
    context_text: str
    tokens_used: int
    token_budget: int
    memory_ids: list[UUID]


class SummarizeMemoryRequest(BaseModel):
    memory_id: UUID
    max_summary_tokens: int = Field(default=250, ge=50, le=2000)


class MemorySummaryResponse(BaseModel):
    summary_id: UUID
    memory_id: UUID
    summary_text: str
    token_count: int


class DeleteMemoryRequest(BaseModel):
    memory_id: UUID
    hard_delete: bool = False


class DeleteMemoryResponse(BaseModel):
    deleted: bool


class MemoryAnalyticsResponse(BaseModel):
    total_memories: int
    total_chunks: int
    total_summaries: int
    avg_chunk_tokens: float
    top_memory_types: dict[str, int]
