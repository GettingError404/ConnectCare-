from __future__ import annotations

from uuid import UUID

from app.repositories.ai_memory_intelligence_async import AIMemoryIntelligenceRepository
from app.services.ai_memory.ranking_engine import RankedCandidate


class AIMemoryContextBuilder:
    """Builds prompt-ready conversation context within a token budget."""

    def __init__(self, repository: AIMemoryIntelligenceRepository):
        self.repository = repository

    async def build_and_persist_context(
        self,
        *,
        tenant_id: UUID,
        conversation_id: UUID,
        user_query: str,
        ranked_results: list[RankedCandidate],
        token_budget: int,
    ):
        context_parts: list[str] = [f"UserQuery: {user_query}", "RelevantMemory:"]
        used = len(user_query.split())
        used_memory_ids: list[UUID] = []

        for item in ranked_results:
            text = item.candidate.chunk_text
            tokens = len(text.split())
            if used + tokens > token_budget:
                break
            context_parts.append(f"- [{item.candidate.source_type}] {text}")
            used += tokens
            if item.candidate.memory_id not in used_memory_ids:
                used_memory_ids.append(item.candidate.memory_id)

        context_text = "\n".join(context_parts)
        context = await self.repository.create_conversation_context(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            context_text=context_text,
            token_budget=token_budget,
            tokens_used=used,
            metadata={
                "memory_ids": [str(x) for x in used_memory_ids],
                "retrieved_count": len(ranked_results),
            },
        )
        return context, used_memory_ids
