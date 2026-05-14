from __future__ import annotations

from uuid import UUID

from app.core.logging import get_logger
from app.schemas.vector_embedding import EmbedBatchRequest, EmbedTextRequest
from app.tasks.vector_embedding_tasks import embed_batch_task, embed_text_task

logger = get_logger(__name__)


class VectorEmbeddingTaskService:
    """Enqueue vector embedding jobs for background processing."""

    @staticmethod
    def enqueue_embed_text(tenant_id: UUID, request: EmbedTextRequest, priority: int = 5) -> str:
        task = embed_text_task.apply_async(
            args=(str(tenant_id), request.model_dump()),
            queue="embedding",
            priority=priority,
        )
        logger.info("vector_embed_text_enqueued", extra={"task_id": task.id, "tenant_id": str(tenant_id)})
        return task.id

    @staticmethod
    def enqueue_embed_batch(tenant_id: UUID, request: EmbedBatchRequest, priority: int = 5) -> str:
        task = embed_batch_task.apply_async(
            args=(str(tenant_id), request.model_dump()),
            queue="embedding",
            priority=priority,
        )
        logger.info("vector_embed_batch_enqueued", extra={"task_id": task.id, "tenant_id": str(tenant_id)})
        return task.id
