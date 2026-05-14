from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.async_session import get_async_db
from app.repositories.vector_embedding_async import DocumentEmbeddingAsyncRepository
from app.schemas.vector_embedding import (
    EmbedBatchRequest,
    EmbedBatchResponse,
    EmbedTextRequest,
    EmbedTextResponse,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
    VectorDocumentCreate,
    VectorDocumentResponse,
)
from app.services.embeddings.orchestration import EmbeddingOrchestrationService

router = APIRouter(prefix="/vectors", tags=["Vectors"])


def require_tenant_id_header(x_tenant_id: UUID = Header(alias="X-Tenant-Id")) -> UUID:
    """Require explicit tenant id for tenant-isolated vector operations."""
    return x_tenant_id


@router.post("/documents", response_model=VectorDocumentResponse)
async def create_vector_document(
    payload: VectorDocumentCreate,
    tenant_id: UUID = Depends(require_tenant_id_header),
    db: AsyncSession = Depends(get_async_db),
):
    repo = DocumentEmbeddingAsyncRepository(db)
    entity = await repo.create_document_embedding(tenant_id=tenant_id, payload=payload)
    return VectorDocumentResponse.model_validate(entity)


@router.post("/search", response_model=SimilaritySearchResponse)
async def search_vectors(
    payload: SimilaritySearchRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    db: AsyncSession = Depends(get_async_db),
):
    repo = DocumentEmbeddingAsyncRepository(db)
    results = await repo.similarity_search(
        tenant_id=tenant_id,
        query_embedding=payload.query_embedding,
        top_k=payload.top_k,
        min_score=payload.min_score,
        source_type=payload.source_type,
    )
    return SimilaritySearchResponse(results=results)


@router.post("/embed-text", response_model=EmbedTextResponse)
async def embed_text(
    payload: EmbedTextRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    db: AsyncSession = Depends(get_async_db),
):
    service = EmbeddingOrchestrationService(db)
    return await service.embed_text(tenant_id=tenant_id, request=payload)


@router.post("/embed-batch", response_model=EmbedBatchResponse)
async def embed_batch(
    payload: EmbedBatchRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    db: AsyncSession = Depends(get_async_db),
):
    service = EmbeddingOrchestrationService(db)
    return await service.embed_batch(tenant_id=tenant_id, request=payload)
