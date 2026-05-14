from __future__ import annotations

from uuid import UUID

from app.tasks.ai_memory_intelligence_tasks import (
    generate_context_task,
    ingest_clinical_task,
    ingest_conversation_task,
    ingest_document_task,
    summarize_memory_task,
)


class AIMemoryIntelligenceTaskService:
    @staticmethod
    def enqueue_ingest_conversation(tenant_id: UUID, user_id: UUID | None, payload: dict, priority: int = 7) -> str:
        task = ingest_conversation_task.apply_async(args=(str(tenant_id), str(user_id) if user_id else None, payload), queue="memory", priority=priority)
        return task.id

    @staticmethod
    def enqueue_ingest_document(tenant_id: UUID, user_id: UUID | None, payload: dict, priority: int = 5) -> str:
        task = ingest_document_task.apply_async(args=(str(tenant_id), str(user_id) if user_id else None, payload), queue="memory", priority=priority)
        return task.id

    @staticmethod
    def enqueue_ingest_clinical(tenant_id: UUID, user_id: UUID | None, payload: dict, priority: int = 9) -> str:
        task = ingest_clinical_task.apply_async(args=(str(tenant_id), str(user_id) if user_id else None, payload), queue="memory", priority=priority)
        return task.id

    @staticmethod
    def enqueue_generate_context(tenant_id: UUID, payload: dict, priority: int = 9) -> str:
        task = generate_context_task.apply_async(args=(str(tenant_id), payload), queue="summarization", priority=priority)
        return task.id

    @staticmethod
    def enqueue_summarize_memory(tenant_id: UUID, payload: dict, priority: int = 6) -> str:
        task = summarize_memory_task.apply_async(args=(str(tenant_id), payload), queue="summarization", priority=priority)
        return task.id
