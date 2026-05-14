from __future__ import annotations

import time
from uuid import UUID

from app.core import metrics as metrics_module
from app.core.logging import get_logger
from app.repositories.ai_memory_intelligence_async import AIMemoryIntelligenceRepository
from app.services.ai_memory.ranking_engine import AIMemoryRankingEngine, RankedCandidate

logger = get_logger(__name__)


class AIMemoryRetrievalEngine:
    """Retrieval pipeline with semantic, hybrid, ranking, and logging."""

    def __init__(self, repository: AIMemoryIntelligenceRepository):
        self.repository = repository
        self.ranking_engine = AIMemoryRankingEngine()

    async def retrieve(
        self,
        *,
        tenant_id: UUID,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
        memory_types: list[str] | None,
        source_types: list[str] | None,
        metadata_filter: dict | None,
        conversation_id: UUID | None,
        use_hybrid_search: bool,
        recency_boost_weight: float,
    ) -> tuple[list[RankedCandidate], str]:
        started = time.perf_counter()
        retrieval_mode = "hybrid" if use_hybrid_search else "semantic"
        try:
            semantic_candidates = await self.repository.semantic_search(
                tenant_id=tenant_id,
                query_embedding=query_embedding,
                top_k=max(top_k * 2, top_k),
                memory_types=memory_types,
                source_types=source_types,
                metadata_filter=metadata_filter,
            )

            keyword_scores = {}
            if use_hybrid_search:
                keyword_scores = await self.repository.hybrid_keyword_search(
                    tenant_id=tenant_id,
                    query=query_text,
                    top_k=max(top_k * 2, top_k),
                )

            ranked = self.ranking_engine.rank(
                candidates=semantic_candidates,
                keyword_scores=keyword_scores,
                recency_boost_weight=recency_boost_weight,
            )[:top_k]

            latency_ms = int((time.perf_counter() - started) * 1000)
            await self.repository.log_retrieval(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                query_text=query_text,
                retrieval_mode=retrieval_mode,
                top_k=top_k,
                latency_ms=latency_ms,
                result_count=len(ranked),
                metadata={"use_hybrid": use_hybrid_search},
            )
            metrics_module.observe_ai_memory_retrieval_latency(retrieval_mode, latency_ms / 1000.0)
            metrics_module.inc_ai_memory_retrieval_requests(retrieval_mode, "success")
            return ranked, retrieval_mode
        except Exception as exc:
            metrics_module.inc_ai_memory_retrieval_requests(retrieval_mode, "failure")
            logger.exception(
                "ai_memory_retrieval_failed",
                extra={
                    "tenant_id": str(tenant_id),
                    "mode": retrieval_mode,
                    "error": str(exc),
                },
            )
            raise
