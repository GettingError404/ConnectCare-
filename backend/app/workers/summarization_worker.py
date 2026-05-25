"""Summarization worker for memory compression.

Lifecycle:
1. Receive conversation_id + tenant_id + time window
2. Load messages/chunks in window from repository
3. Generate summary (stub - no LLM calls per requirements)
4. Create summary and associate chunks
5. Track metrics
6. Handle idempotency via summary_hash deduplication

Idempotency:
- If summary exists for window with same hash, skip generation
- Track summary_version for re-summarization detection
"""
from __future__ import annotations

import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.logging import tenant_id_ctx
from app.repositories.ai_memory import AIMemoryRepository
from app.workers import TenantAwareTask, QueueName, RetryConfig
from app.core import metrics as metrics_module

logger = logging.getLogger(__name__)

SUMMARY_MODEL = "placeholder-summary-model"
SUMMARY_VERSION = "v1"
DEFAULT_WINDOW_SIZE_MINUTES = 60


def _coerce_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


class SummarizationTask(TenantAwareTask):
    """Task for generating conversation summaries"""
    
    name = "ai_memory.summarization.generate"
    queue = QueueName.SUMMARIZATION.value
    priority = 8
    soft_time_limit = 600  # 10 minutes
    time_limit = 900  # Hard limit 15 minutes
    max_retries = RetryConfig.RETRY_MAX_RETRIES
    
    def execute_tenant_aware(
        self,
        db: Session,
        tenant_id: UUID,
        conversation_id: UUID,
        window_start_at: Optional[datetime] = None,
        window_end_at: Optional[datetime] = None,
        summary_version: str = SUMMARY_VERSION,
    ) -> dict:
        """Generate and store summary for conversation window.
        
        Args:
            db: SQLAlchemy session
            tenant_id: Tenant UUID
            conversation_id: Conversation UUID
            window_start_at: Start of summarization window (optional)
            window_end_at: End of summarization window (optional)
            summary_version: Version string for re-summarization tracking
            
        Returns:
            Dict with summary_id, status, and metrics
        """
        repo = AIMemoryRepository(db)
        
        try:
            # Load conversation
            conversation = repo.get_conversation(tenant_id, conversation_id)
            if not conversation:
                logger.warning(
                    "conversation_not_found",
                    extra={
                        "conversation_id": str(conversation_id),
                        "tenant_id": str(tenant_id),
                    },
                )
                return {"status": "conversation_not_found", "summary_id": None}
            
            # Get messages in window
            window_end = window_end_at or datetime.utcnow()
            window_start = window_start_at or (window_end - timedelta(minutes=DEFAULT_WINDOW_SIZE_MINUTES))
            
            messages = repo.get_recent_messages(tenant_id, conversation_id, limit=100)
            
            # Filter by window
            windowed_messages = [
                m for m in messages
                if window_start <= (m.recorded_at or m.created_at) <= window_end
            ]
            
            if not windowed_messages:
                logger.info(
                    "no_messages_in_window",
                    extra={
                        "conversation_id": str(conversation_id),
                        "window_start": window_start.isoformat(),
                        "window_end": window_end.isoformat(),
                    },
                )
                return {
                    "status": "no_messages",
                    "summary_id": None,
                    "message_count": 0,
                }
            
            # Generate summary text and hash
            summary_text, summary_hash = _generate_summary(windowed_messages)
            
            # Check for duplicate summary (idempotency)
            existing_summaries = repo.get_conversation_summaries(tenant_id, conversation_id)
            for existing in existing_summaries:
                if existing.summary_hash == summary_hash:
                    logger.info(
                        "summary_already_exists",
                        extra={
                            "conversation_id": str(conversation_id),
                            "summary_id": str(existing.id),
                            "message_count": len(windowed_messages),
                        },
                    )
                    return {
                        "status": "already_summarized",
                        "summary_id": str(existing.id),
                        "message_count": len(windowed_messages),
                    }
            
            # Store summary
            summary = repo.create_summary(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                summary_text=summary_text,
                summary_hash=summary_hash,
                source_window_start_at=window_start,
                source_window_end_at=window_end,
                summary_version=summary_version,
            )
            
            logger.info(
                "summary_stored",
                extra={
                    "conversation_id": str(conversation_id),
                    "summary_id": str(summary.id),
                    "message_count": len(windowed_messages),
                    "summary_length": len(summary_text),
                },
            )
            
            metrics_module.inc_ai_memory_summaries_generated()
            
            return {
                "status": "success",
                "summary_id": str(summary.id),
                "conversation_id": str(conversation_id),
                "message_count": len(windowed_messages),
                "summary_length": len(summary_text),
            }
        
        except Exception as exc:
            logger.exception(
                "summarization_failed",
                extra={
                    "conversation_id": str(conversation_id),
                    "tenant_id": str(tenant_id),
                },
                exc_info=exc,
            )
            metrics_module.inc_ai_memory_summaries_failed()
            raise


def _generate_summary(messages: List) -> tuple[str, str]:
    """Generate summary from messages.
    
    PLACEHOLDER: Production implementation would call LLM API.
    This is per requirements - no LLM/external API calls.
    
    Args:
        messages: List of AIMessage objects
        
    Returns:
        Tuple of (summary_text, summary_hash)
    """
    # Stub: concatenate first 50 chars of each message as "summary"
    # In production, call: openai.ChatCompletion.create(
    #     model="gpt-4",
    #     messages=[{"role": m.role, "content": m.content} for m in messages],
    #     ...
    # )
    import hashlib
    
    message_texts = [m.content[:50] for m in messages]
    summary_text = " ".join(message_texts)
    
    summary_hash = hashlib.sha256(summary_text.encode()).hexdigest()
    
    return summary_text, summary_hash


@celery_app.task(
    bind=True,
    base=SummarizationTask,
    **RetryConfig.get_autoretry_config(),
)
def summarize_conversation_window(
    self,
    tenant_id: str,
    conversation_id: str,
    window_start_at: Optional[str] = None,
    window_end_at: Optional[str] = None,
    summary_version: str = SUMMARY_VERSION,
) -> dict:
    """Celery task: generate summary for conversation time window.
    
    Args:
        tenant_id: Tenant UUID string
        conversation_id: Conversation UUID string
        window_start_at: Window start ISO datetime string (optional)
        window_end_at: Window end ISO datetime string (optional)
        summary_version: Version string
        
    Returns:
        Task result dict
    """
    parsed_start = datetime.fromisoformat(window_start_at) if window_start_at else None
    parsed_end = datetime.fromisoformat(window_end_at) if window_end_at else None
    
    return SummarizationTask.run(
        self,
        tenant_id=_coerce_uuid(tenant_id),
        conversation_id=_coerce_uuid(conversation_id),
        window_start_at=parsed_start,
        window_end_at=parsed_end,
        summary_version=summary_version,
    )


@celery_app.task(
    bind=True,
    base=SummarizationTask,
    queue=QueueName.MEMORY.value,
    **RetryConfig.get_autoretry_config(),
)
def schedule_periodic_summarization(
    self,
    tenant_id: str,
    conversation_id: str,
    window_size_minutes: int = DEFAULT_WINDOW_SIZE_MINUTES,
) -> dict:
    """Celery task: enqueue summarization for all windows in conversation.
    
    Useful for background periodic jobs that summarize entire conversations.
    
    Args:
        tenant_id: Tenant UUID string
        conversation_id: Conversation UUID string
        window_size_minutes: Size of summarization windows
        
    Returns:
        Task result dict with count of enqueued summaries
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
        
        # Get all messages in conversation
        messages = repo.get_recent_messages(tenant_uuid, conversation_uuid, limit=1000)
        
        if not messages:
            logger.info(
                "no_messages_for_summarization",
                extra={
                    "conversation_id": str(conversation_uuid),
                    "tenant_id": str(tenant_uuid),
                },
            )
            return {
                "status": "no_messages",
                "summarization_tasks_enqueued": 0,
            }
        
        # Calculate windows
        windows = []
        earliest = min(m.recorded_at or m.created_at for m in messages)
        latest = max(m.recorded_at or m.created_at for m in messages)
        
        current = earliest
        while current < latest:
            window_end = current + timedelta(minutes=window_size_minutes)
            windows.append((current, window_end))
            current = window_end
        
        # Enqueue summarization tasks
        for window_start, window_end in windows:
            summarize_conversation_window.apply_async(
                args=(str(tenant_uuid), str(conversation_uuid)),
                kwargs={
                    "window_start_at": window_start.isoformat(),
                    "window_end_at": window_end.isoformat(),
                },
                queue=QueueName.SUMMARIZATION.value,
                priority=7,
            )
        
        logger.info(
            "summarization_windows_enqueued",
            extra={
                "conversation_id": str(conversation_uuid),
                "tenant_id": str(tenant_uuid),
                "window_count": len(windows),
            },
        )
        
        return {
            "status": "enqueued",
            "conversation_id": str(conversation_uuid),
            "summarization_tasks_enqueued": len(windows),
        }
    
    except Exception as exc:
        logger.exception(
            "summarization_scheduling_failed",
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
