"""AI Memory task service layer.

Provides high-level API for enqueueing AI memory processing tasks.
Handles task creation, priority routing, and result tracking.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.tasks.ai_memory_tasks import (
    generate_chunk_embedding,
    generate_conversation_embeddings,
    summarize_conversation_window,
    schedule_periodic_summarization,
)
from app.workers import QueueName

logger = logging.getLogger(__name__)


class AIMemoryTaskService:
    """Service for enqueueing AI memory processing tasks"""
    
    # Task priority levels (higher = higher priority)
    PRIORITY_CRITICAL = 10
    PRIORITY_HIGH = 8
    PRIORITY_NORMAL = 5
    PRIORITY_LOW = 1
    
    @staticmethod
    def enqueue_embedding_for_chunk(
        tenant_id: UUID,
        chunk_id: UUID,
        embedding_model: str = "placeholder-embedding-model",
        embedding_version: str = "v1",
        priority: int = PRIORITY_HIGH,
    ) -> str:
        """Enqueue embedding task for single chunk.
        
        Args:
            tenant_id: Tenant UUID
            chunk_id: Chunk UUID to embed
            embedding_model: Model identifier
            embedding_version: Version string
            priority: Queue priority (1-10, higher = sooner)
            
        Returns:
            Task ID for tracking
        """
        task = generate_chunk_embedding.apply_async(
            args=(str(tenant_id), str(chunk_id)),
            kwargs={
                "embedding_model": embedding_model,
                "embedding_version": embedding_version,
            },
            queue=QueueName.EMBEDDING.value,
            priority=priority,
        )
        
        logger.info(
            "embedding_task_enqueued",
            extra={
                "task_id": task.id,
                "chunk_id": str(chunk_id),
                "tenant_id": str(tenant_id),
                "priority": priority,
            },
        )
        
        return task.id
    
    @staticmethod
    def enqueue_embeddings_for_conversation(
        tenant_id: UUID,
        conversation_id: UUID,
        embedding_model: str = "placeholder-embedding-model",
        embedding_version: str = "v1",
        priority: int = PRIORITY_NORMAL,
    ) -> str:
        """Enqueue embedding batch task for entire conversation.
        
        This enqueues a task that will fetch all chunks and enqueue individual
        embedding tasks. Useful for bulk operations.
        
        Args:
            tenant_id: Tenant UUID
            conversation_id: Conversation UUID
            embedding_model: Model identifier
            embedding_version: Version string
            priority: Queue priority
            
        Returns:
            Task ID for the batch task
        """
        task = generate_conversation_embeddings.apply_async(
            args=(str(tenant_id), str(conversation_id)),
            kwargs={
                "embedding_model": embedding_model,
                "embedding_version": embedding_version,
            },
            queue=QueueName.MEMORY.value,
            priority=priority,
        )
        
        logger.info(
            "conversation_embeddings_batch_enqueued",
            extra={
                "task_id": task.id,
                "conversation_id": str(conversation_id),
                "tenant_id": str(tenant_id),
                "priority": priority,
            },
        )
        
        return task.id
    
    @staticmethod
    def enqueue_summary_for_window(
        tenant_id: UUID,
        conversation_id: UUID,
        window_start_at: Optional[datetime] = None,
        window_end_at: Optional[datetime] = None,
        summary_version: str = "v1",
        priority: int = PRIORITY_NORMAL,
    ) -> str:
        """Enqueue summarization task for conversation time window.
        
        Args:
            tenant_id: Tenant UUID
            conversation_id: Conversation UUID
            window_start_at: Window start datetime (optional)
            window_end_at: Window end datetime (optional)
            summary_version: Version string
            priority: Queue priority
            
        Returns:
            Task ID for tracking
        """
        task = summarize_conversation_window.apply_async(
            args=(str(tenant_id), str(conversation_id)),
            kwargs={
                "window_start_at": window_start_at.isoformat() if window_start_at else None,
                "window_end_at": window_end_at.isoformat() if window_end_at else None,
                "summary_version": summary_version,
            },
            queue=QueueName.SUMMARIZATION.value,
            priority=priority,
        )
        
        logger.info(
            "summary_task_enqueued",
            extra={
                "task_id": task.id,
                "conversation_id": str(conversation_id),
                "tenant_id": str(tenant_id),
                "priority": priority,
            },
        )
        
        return task.id
    
    @staticmethod
    def enqueue_periodic_summarization(
        tenant_id: UUID,
        conversation_id: UUID,
        window_size_minutes: int = 60,
        priority: int = PRIORITY_LOW,
    ) -> str:
        """Enqueue batch task to summarize all windows in conversation.
        
        Args:
            tenant_id: Tenant UUID
            conversation_id: Conversation UUID
            window_size_minutes: Size of each summarization window
            priority: Queue priority (usually low for background ops)
            
        Returns:
            Task ID for the batch task
        """
        task = schedule_periodic_summarization.apply_async(
            args=(str(tenant_id), str(conversation_id)),
            kwargs={
                "window_size_minutes": window_size_minutes,
            },
            queue=QueueName.MEMORY.value,
            priority=priority,
        )
        
        logger.info(
            "periodic_summarization_batch_enqueued",
            extra={
                "task_id": task.id,
                "conversation_id": str(conversation_id),
                "tenant_id": str(tenant_id),
                "priority": priority,
            },
        )
        
        return task.id
    
    @staticmethod
    def get_task_status(task_id: str) -> dict:
        """Get status of an enqueued task.
        
        Args:
            task_id: Celery task ID
            
        Returns:
            Dict with task status and result
        """
        from app.core.celery_app import celery_app
        
        result = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.successful() else None,
            "error": str(result.info) if result.failed() else None,
        }
