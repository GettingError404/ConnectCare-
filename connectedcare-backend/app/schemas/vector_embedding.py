from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


class VectorDocumentCreate(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    source_id: UUID
    content: str = Field(min_length=1)
    embedding_model: str = Field(default="example-embedding-v1", min_length=1, max_length=128)
    embedding: list[float]
    metadata: dict | None = None

    @field_validator("embedding")
    @classmethod
    def validate_embedding_dimension(cls, value: list[float]) -> list[float]:
        expected_dim = settings.PGVECTOR_EMBEDDING_DIMENSION
        if len(value) != expected_dim:
            raise ValueError(f"embedding length must be exactly {expected_dim}")
        return value


class SimilaritySearchRequest(BaseModel):
    query_embedding: list[float]
    top_k: int = Field(default=10, ge=1, le=100)
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    source_type: str | None = Field(default=None, max_length=64)

    @field_validator("query_embedding")
    @classmethod
    def validate_query_embedding_dimension(cls, value: list[float]) -> list[float]:
        expected_dim = settings.PGVECTOR_EMBEDDING_DIMENSION
        if len(value) != expected_dim:
            raise ValueError(f"query_embedding length must be exactly {expected_dim}")
        return value


class VectorDocumentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    source_type: str
    source_id: UUID
    content: str
    embedding_model: str
    embedding_dimension: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SimilaritySearchResult(BaseModel):
    id: UUID
    tenant_id: UUID
    source_type: str
    source_id: UUID
    content: str
    distance: float
    score: float


class SimilaritySearchResponse(BaseModel):
    results: list[SimilaritySearchResult]


class EmbedTextRequest(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    source_id: UUID
    text: str = Field(min_length=1)
    metadata: dict | None = None
    provider: str | None = Field(default=None, max_length=64)
    embedding_model: str | None = Field(default=None, max_length=128)
    chunk_size_tokens: int | None = Field(default=None, ge=1)
    chunk_overlap_tokens: int | None = Field(default=None, ge=0)


class EmbeddedChunkResult(BaseModel):
    chunk_index: int
    chunk_text: str
    token_estimate: int
    document: VectorDocumentResponse


class EmbedTextResponse(BaseModel):
    provider: str
    embedding_model: str
    chunk_count: int
    duration_seconds: float
    chunks: list[EmbeddedChunkResult]


class EmbedBatchItem(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    source_id: UUID
    text: str = Field(min_length=1)
    metadata: dict | None = None


class EmbedBatchRequest(BaseModel):
    items: list[EmbedBatchItem] = Field(min_length=1, max_length=100)
    provider: str | None = Field(default=None, max_length=64)
    embedding_model: str | None = Field(default=None, max_length=128)
    chunk_size_tokens: int | None = Field(default=None, ge=1)
    chunk_overlap_tokens: int | None = Field(default=None, ge=0)


class EmbedBatchResultItem(BaseModel):
    source_type: str
    source_id: UUID
    status: str
    chunk_count: int
    chunks: list[EmbeddedChunkResult]
    error: str | None = None


class EmbedBatchResponse(BaseModel):
    provider: str
    embedding_model: str
    total: int
    succeeded: int
    failed: int
    duration_seconds: float
    items: list[EmbedBatchResultItem]
