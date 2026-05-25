"""Embedding worker for vector generation.

Lifecycle:
1. Receive chunk_id + tenant_id
2. Load chunk from repository
3. Generate embedding vector (stub - no LLM calls per requirements)
4. Store embedding in database
5. Track metrics
6. Handle idempotency via content_hash deduplication

Idempotency:
- If embedding exists for chunk_id+embedding_model, skip generation
- Use content_hash to detect content changes requiring re-embedding
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.logging import tenant_id_ctx
from app.models.ai_memory import EMBEDDING_DIMENSION
from app.repositories.ai_memory import AIMemoryRepository
from app.workers import TenantAwareTask, QueueName, RetryConfig
from app.core import metrics as metrics_module

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "placeholder-embedding-model"  # Replace with actual model name
EMBEDDING_VERSION = "v1"


def _coerce_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


class EmbeddingTask(TenantAwareTask):
    """Task for generating and storing vector embeddings for chunks"""
    
    name = "ai_memory.embedding.generate"
    queue = QueueName.EMBEDDING.value
    priority = 10  # Highest priority in embedding queue
    soft_time_limit = 300  # 5 minutes
    time_limit = 600  # Hard limit 10 minutes
    max_retries = RetryConfig.RETRY_MAX_RETRIES
    
    def execute_tenant_aware(
        self,
        db: Session,
        tenant_id: UUID,
        chunk_id: UUID,
        embedding_model: str = EMBEDDING_MODEL,
        embedding_version: str = EMBEDDING_VERSION,
    ) -> dict:
        """Generate and store embedding for chunk.
        
        Args:
            db: SQLAlchemy session
            tenant_id: Tenant UUID
            chunk_id: Chunk UUID to embed
            embedding_model: Model identifier (for versioning)
            embedding_version: Version string for re-embedding tracking
            
        Returns:
            Dict with embedding_id, status, and metrics
        """
        repo = AIMemoryRepository(db)
        
        try:
            # Load chunk
            chunk = repo.get_chunk(tenant_id, chunk_id)
            if not chunk:
                logger.warning(
                    "chunk_not_found",
                    extra={
                        "chunk_id": str(chunk_id),
                        "tenant_id": str(tenant_id),
                    },
                )
                return {"status": "chunk_not_found", "embedding_id": None}
            
            # Check for existing embedding (idempotency)
            existing = repo.get_embedding(tenant_id, chunk_id)
            if existing and existing.embedding_model == embedding_model:
                # Check if content changed (via hash)
                if existing.content_hash == chunk.chunk_hash:
                    logger.info(
                        "embedding_already_exists",
                        extra={
                            "chunk_id": str(chunk_id),
                            "embedding_id": str(existing.id),
                        },
                    )
                    return {
                        "status": "already_embedded",
                        "embedding_id": str(existing.id),
                    }
                else:
                    logger.info(
                        "content_changed_regenerating_embedding",
                        extra={
                            "chunk_id": str(chunk_id),
                            "old_hash": existing.content_hash,
                            "new_hash": chunk.chunk_hash,
                        },
                    )
            
            # Generate embedding vector
            embedding_vector = _generate_embedding_vector(chunk.chunk_text)
            
            # Store embedding
            embedding = repo.store_embedding(
                tenant_id=tenant_id,
                chunk_id=chunk_id,
                embedding=embedding_vector,
                embedding_model=embedding_model,
                content_hash=chunk.chunk_hash,
                embedding_version=embedding_version,
                embedded_at=datetime.utcnow(),
            )
            
            logger.info(
                "embedding_stored",
                extra={
                    "chunk_id": str(chunk_id),
                    "embedding_id": str(embedding.id),
                    "embedding_model": embedding_model,
                    "embedding_dimension": len(embedding_vector),
                },
            )
            
            metrics_module.inc_ai_memory_embeddings_generated(embedding_model)
            
            return {
                "status": "success",
                "embedding_id": str(embedding.id),
                "chunk_id": str(chunk_id),
                "embedding_dimension": len(embedding_vector),
            }
        
        except Exception as exc:
            logger.exception(
                "embedding_generation_failed",
                extra={
                    "chunk_id": str(chunk_id),
                    "tenant_id": str(tenant_id),
                },
                exc_info=exc,
            )
            metrics_module.inc_ai_memory_embeddings_failed(embedding_model)
            raise


def _generate_embedding_vector(text: str) -> list[float]:
    """Generate embedding vector for text.
    
    PLACEHOLDER: Production implementation would call embedding API.
    This is per requirements - no LLM/external API calls.
    
    Args:
        text: Text to embed
        
    Returns:
        List of 1536 floats (OpenAI embedding dimension)
    """
    # Stub: return zeros with correct dimension
    # In production, call: openai.Embedding.create(text=text, model="text-embedding-3-small")
    return [0.0] * EMBEDDING_DIMENSION


@celery_app.task(
    bind=True,
    base=EmbeddingTask,
    **RetryConfig.get_autoretry_config(),
)
def generate_chunk_embedding(
    self,
    tenant_id: str,
    chunk_id: str,
    embedding_model: str = EMBEDDING_MODEL,
    embedding_version: str = EMBEDDING_VERSION,
) -> dict:
    """Celery task: generate embedding for chunk.
    
    Args:
        tenant_id: Tenant UUID string
        chunk_id: Chunk UUID string
        embedding_model: Model identifier
        embedding_version: Version string
        
    Returns:
        Task result dict
    """
    return EmbeddingTask.run(
        self,
        tenant_id=_coerce_uuid(tenant_id),
        chunk_id=_coerce_uuid(chunk_id),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
    )


@celery_app.task(
    bind=True,
    base=EmbeddingTask,
    queue=QueueName.MEMORY.value,
    **RetryConfig.get_autoretry_config(),
)
def generate_conversation_embeddings(
    self,
    tenant_id: str,
    conversation_id: str,
    embedding_model: str = EMBEDDING_MODEL,
    embedding_version: str = EMBEDDING_VERSION,
) -> dict:
    """Celery task: generate embeddings for all chunks in conversation.
    
    Fetches all chunks, enqueues individual embedding tasks.
    
    Args:
        tenant_id: Tenant UUID string
        conversation_id: Conversation UUID string
        embedding_model: Model identifier
        embedding_version: Version string
        
    Returns:
        Task result dict with count of enqueued tasks
    """
    tenant_uuid = _coerce_uuid(tenant_id)
    conversation_uuid = _coerce_uuid(conversation_id)
    
    tenant_id_ctx.set(str(tenant_uuid))
    
    db = None
    try:
        from app.db.session import SessionLocal
        from app.repositories.ai_memory import AIMemoryRepository
        
        db = SessionLocal()
        repo = AIMemoryRepository(db)
        
        # Get all chunks for conversation
        chunks = db.query(
            __import__("app.models.ai_memory", fromlist=["AIMemoryChunk"]).AIMemoryChunk
        ).filter(
            __import__("app.models.ai_memory", fromlist=["AIMemoryChunk"]).AIMemoryChunk.tenant_id == tenant_uuid,
            __import__("app.models.ai_memory", fromlist=["AIMemoryChunk"]).AIMemoryChunk.conversation_id == conversation_uuid,
            __import__("app.models.ai_memory", fromlist=["AIMemoryChunk"]).AIMemoryChunk.deleted_at.is_(None),
        ).all()
        
        enqueued_count = 0
        for chunk in chunks:
            generate_chunk_embedding.apply_async(
                args=(str(tenant_uuid), str(chunk.id)),
                kwargs={
                    "embedding_model": embedding_model,
                    "embedding_version": embedding_version,
                },
                queue=QueueName.EMBEDDING.value,
                priority=9,
            )
            enqueued_count += 1
        
        logger.info(
            "conversation_embeddings_enqueued",
            extra={
                "conversation_id": str(conversation_uuid),
                "tenant_id": str(tenant_uuid),
                "chunk_count": enqueued_count,
            },
        )
        
        return {
            "status": "enqueued",
            "conversation_id": str(conversation_uuid),
            "chunk_count": enqueued_count,
        }
    
    except Exception as exc:
        logger.exception(
            "conversation_embeddings_enqueue_failed",
            extra={
                "conversation_id": str(conversation_uuid),
                "tenant_id": str(tenant_uuid),
            },
            exc_info=exc,
        )
        raise
    
    finally:
        if db:
            db.close()
