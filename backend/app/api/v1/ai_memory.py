from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.async_session import get_async_db
from app.schemas.ai_memory import (
    ClinicalNoteMemoryIngestRequest,
    ConversationMemoryIngestRequest,
    DeleteMemoryRequest,
    DeleteMemoryResponse,
    DocumentMemoryIngestRequest,
    GenerateContextRequest,
    GenerateContextResponse,
    MemoryAnalyticsResponse,
    MemoryIngestResponse,
    MemoryRetrieveRequest,
    MemoryRetrieveResponse,
    MemorySearchRequest,
    MemorySummaryResponse,
    SummarizeMemoryRequest,
)
from app.services.ai_memory.orchestration import AIMemoryOrchestrationService

router = APIRouter(prefix="/memory", tags=["AI Memory"])


def require_tenant_id_header(x_tenant_id: UUID = Header(alias="X-Tenant-Id")) -> UUID:
    return x_tenant_id


@router.post("/ingest/conversation", response_model=MemoryIngestResponse)
async def ingest_conversation_memory(
    payload: ConversationMemoryIngestRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = AIMemoryOrchestrationService(db)
    return await service.ingest_conversation_memory(
        tenant_id=tenant_id,
        user_id=getattr(current_user, "id", None),
        payload=payload,
    )


@router.post("/ingest/document", response_model=MemoryIngestResponse)
async def ingest_document_memory(
    payload: DocumentMemoryIngestRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = AIMemoryOrchestrationService(db)
    return await service.ingest_document_memory(
        tenant_id=tenant_id,
        user_id=getattr(current_user, "id", None),
        payload=payload,
    )


@router.post("/ingest/clinical-note", response_model=MemoryIngestResponse)
async def ingest_clinical_note_memory(
    payload: ClinicalNoteMemoryIngestRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = AIMemoryOrchestrationService(db)
    return await service.ingest_clinical_note_memory(
        tenant_id=tenant_id,
        user_id=getattr(current_user, "id", None),
        payload=payload,
    )


@router.post("/retrieve", response_model=MemoryRetrieveResponse)
async def retrieve_memory(
    payload: MemoryRetrieveRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    db: AsyncSession = Depends(get_async_db),
):
    service = AIMemoryOrchestrationService(db)
    return await service.retrieve_memories(tenant_id=tenant_id, payload=payload)


@router.post("/search", response_model=MemoryRetrieveResponse)
async def search_memory(
    payload: MemorySearchRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    db: AsyncSession = Depends(get_async_db),
):
    service = AIMemoryOrchestrationService(db)
    request = MemoryRetrieveRequest(query=payload.query, top_k=payload.top_k, metadata_filter=payload.metadata_filter)
    return await service.retrieve_memories(tenant_id=tenant_id, payload=request)


@router.post("/context", response_model=GenerateContextResponse)
async def generate_conversation_context(
    payload: GenerateContextRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    db: AsyncSession = Depends(get_async_db),
):
    service = AIMemoryOrchestrationService(db)
    return await service.generate_context(tenant_id=tenant_id, payload=payload)


@router.post("/summarize", response_model=MemorySummaryResponse)
async def summarize_memory(
    payload: SummarizeMemoryRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    db: AsyncSession = Depends(get_async_db),
):
    service = AIMemoryOrchestrationService(db)
    response = await service.summarize_memory(tenant_id=tenant_id, payload=payload)
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return response


@router.delete("/delete", response_model=DeleteMemoryResponse)
async def delete_memory(
    payload: DeleteMemoryRequest,
    tenant_id: UUID = Depends(require_tenant_id_header),
    db: AsyncSession = Depends(get_async_db),
):
    service = AIMemoryOrchestrationService(db)
    deleted = await service.delete_memory(tenant_id=tenant_id, payload=payload)
    return DeleteMemoryResponse(deleted=deleted)


@router.get("/analytics", response_model=MemoryAnalyticsResponse)
async def memory_analytics(
    tenant_id: UUID = Depends(require_tenant_id_header),
    db: AsyncSession = Depends(get_async_db),
):
    service = AIMemoryOrchestrationService(db)
    return await service.analytics(tenant_id=tenant_id)
