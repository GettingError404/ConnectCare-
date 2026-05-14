"""AI Memory Celery task definitions.

This module re-exports worker tasks for external consumption.
All tasks are defined in app/workers/* and imported here for convenience.
"""
from __future__ import annotations

from app.workers.embedding_worker import (
    generate_chunk_embedding,
    generate_conversation_embeddings,
)
from app.workers.summarization_worker import (
    summarize_conversation_window,
    schedule_periodic_summarization,
)

__all__ = [
    "generate_chunk_embedding",
    "generate_conversation_embeddings",
    "summarize_conversation_window",
    "schedule_periodic_summarization",
]
