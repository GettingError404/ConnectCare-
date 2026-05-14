from __future__ import annotations

import hashlib
from uuid import UUID

from app.repositories.ai_memory_intelligence_async import AIMemoryIntelligenceRepository


class AIMemorySummarizationService:
    """Deterministic summarization and memory compression service.

    This extractive summarizer is provider-independent and safe for background workers.
    """

    def __init__(self, repository: AIMemoryIntelligenceRepository):
        self.repository = repository

    @staticmethod
    def _compress_text(content: str, max_tokens: int) -> str:
        words = content.split()
        if len(words) <= max_tokens:
            return content
        head = words[: max_tokens // 2]
        tail = words[-(max_tokens // 2) :]
        return " ".join(head + ["..."] + tail)

    async def summarize_memory(
        self,
        *,
        tenant_id: UUID,
        memory_id: UUID,
        max_summary_tokens: int,
    ):
        memory = await self.repository.get_memory(tenant_id=tenant_id, memory_id=memory_id)
        if memory is None:
            return None

        summary_text = self._compress_text(memory.content, max_summary_tokens)
        # Compression marker helps downstream retrieval pipelines decide context granularity.
        metadata = {
            "compression": "extractive",
            "content_hash": hashlib.sha256(memory.content.encode("utf-8")).hexdigest(),
        }
        chunks = await self.repository.list_memory_chunks(tenant_id=tenant_id, memory_id=memory_id)
        return await self.repository.create_summary(
            tenant_id=tenant_id,
            memory_id=memory_id,
            summary_text=summary_text,
            source_chunk_count=len(chunks),
            metadata=metadata,
        )
