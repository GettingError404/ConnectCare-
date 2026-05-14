"""Celery tasks for AI memory intelligence pipelines."""
from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.db.async_session import AsyncSessionLocal
from app.schemas.ai_memory import (
    ClinicalNoteMemoryIngestRequest,
    ConversationMemoryIngestRequest,
    DocumentMemoryIngestRequest,
    GenerateContextRequest,
    SummarizeMemoryRequest,
)
from app.services.ai_memory.orchestration import AIMemoryOrchestrationService

logger = get_logger(__name__)


async def _run_ingest_conversation(tenant_id: UUID, user_id: UUID | None, payload: ConversationMemoryIngestRequest) -> dict:
    async with AsyncSessionLocal() as db:
        service = AIMemoryOrchestrationService(db)
        response = await service.ingest_conversation_memory(tenant_id=tenant_id, user_id=user_id, payload=payload)
        return response.model_dump(mode="json")


async def _run_ingest_document(tenant_id: UUID, user_id: UUID | None, payload: DocumentMemoryIngestRequest) -> dict:
    async with AsyncSessionLocal() as db:
        service = AIMemoryOrchestrationService(db)
        response = await service.ingest_document_memory(tenant_id=tenant_id, user_id=user_id, payload=payload)
        return response.model_dump(mode="json")


async def _run_ingest_clinical(tenant_id: UUID, user_id: UUID | None, payload: ClinicalNoteMemoryIngestRequest) -> dict:
    async with AsyncSessionLocal() as db:
        service = AIMemoryOrchestrationService(db)
        response = await service.ingest_clinical_note_memory(tenant_id=tenant_id, user_id=user_id, payload=payload)
        return response.model_dump(mode="json")


async def _run_generate_context(tenant_id: UUID, payload: GenerateContextRequest) -> dict:
    async with AsyncSessionLocal() as db:
        service = AIMemoryOrchestrationService(db)
        response = await service.generate_context(tenant_id=tenant_id, payload=payload)
        return response.model_dump(mode="json")


async def _run_summarize(tenant_id: UUID, payload: SummarizeMemoryRequest) -> dict:
    async with AsyncSessionLocal() as db:
        service = AIMemoryOrchestrationService(db)
        response = await service.summarize_memory(tenant_id=tenant_id, payload=payload)
        return response.model_dump(mode="json") if response else {"summary_id": None}


@celery_app.task(bind=True, name="ai_memory_intelligence.ingest_conversation", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def ingest_conversation_task(self, tenant_id: str, user_id: str | None, payload: dict) -> dict:
    logger.info("ai_memory_intelligence.ingest_conversation.start", extra={"tenant_id": tenant_id})
    parsed = ConversationMemoryIngestRequest.model_validate(payload)
    return asyncio.run(_run_ingest_conversation(UUID(tenant_id), UUID(user_id) if user_id else None, parsed))


@celery_app.task(bind=True, name="ai_memory_intelligence.ingest_document", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def ingest_document_task(self, tenant_id: str, user_id: str | None, payload: dict) -> dict:
    logger.info("ai_memory_intelligence.ingest_document.start", extra={"tenant_id": tenant_id})
    parsed = DocumentMemoryIngestRequest.model_validate(payload)
    return asyncio.run(_run_ingest_document(UUID(tenant_id), UUID(user_id) if user_id else None, parsed))


@celery_app.task(bind=True, name="ai_memory_intelligence.ingest_clinical", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def ingest_clinical_task(self, tenant_id: str, user_id: str | None, payload: dict) -> dict:
    logger.info("ai_memory_intelligence.ingest_clinical.start", extra={"tenant_id": tenant_id})
    parsed = ClinicalNoteMemoryIngestRequest.model_validate(payload)
    return asyncio.run(_run_ingest_clinical(UUID(tenant_id), UUID(user_id) if user_id else None, parsed))


@celery_app.task(bind=True, name="ai_memory_intelligence.generate_context", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def generate_context_task(self, tenant_id: str, payload: dict) -> dict:
    logger.info("ai_memory_intelligence.generate_context.start", extra={"tenant_id": tenant_id})
    parsed = GenerateContextRequest.model_validate(payload)
    return asyncio.run(_run_generate_context(UUID(tenant_id), parsed))


@celery_app.task(bind=True, name="ai_memory_intelligence.summarize", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def summarize_memory_task(self, tenant_id: str, payload: dict) -> dict:
    logger.info("ai_memory_intelligence.summarize.start", extra={"tenant_id": tenant_id})
    parsed = SummarizeMemoryRequest.model_validate(payload)
    return asyncio.run(_run_summarize(UUID(tenant_id), parsed))
