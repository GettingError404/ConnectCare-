"""Celery-ready vector embedding tasks.

These tasks are queue-safe wrappers around the async embedding orchestration service.
They can be enqueued now and executed once workers import this module.
"""
from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.db.async_session import AsyncSessionLocal
from app.schemas.vector_embedding import EmbedBatchRequest, EmbedTextRequest
from app.services.embeddings.orchestration import EmbeddingOrchestrationService

logger = get_logger(__name__)


async def _run_embed_text_task(tenant_id: UUID, payload: EmbedTextRequest) -> dict:
    async with AsyncSessionLocal() as session:
        service = EmbeddingOrchestrationService(session)
        response = await service.embed_text(tenant_id=tenant_id, request=payload)
        return response.model_dump()


async def _run_embed_batch_task(tenant_id: UUID, payload: EmbedBatchRequest) -> dict:
    async with AsyncSessionLocal() as session:
        service = EmbeddingOrchestrationService(session)
        response = await service.embed_batch(tenant_id=tenant_id, request=payload)
        return response.model_dump()


@celery_app.task(bind=True, name="vectors.embed_text", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def embed_text_task(self, tenant_id: str, payload: dict) -> dict:
    logger.info("vector_embed_text_task_started", extra={"tenant_id": tenant_id})
    request = EmbedTextRequest.model_validate(payload)
    return asyncio.run(_run_embed_text_task(UUID(tenant_id), request))


@celery_app.task(bind=True, name="vectors.embed_batch", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def embed_batch_task(self, tenant_id: str, payload: dict) -> dict:
    logger.info("vector_embed_batch_task_started", extra={"tenant_id": tenant_id})
    request = EmbedBatchRequest.model_validate(payload)
    return asyncio.run(_run_embed_batch_task(UUID(tenant_id), request))
