from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.ai_memory_intelligence_async import RetrievalCandidate


@dataclass
class RankedCandidate:
    candidate: RetrievalCandidate
    hybrid_score: float
    recency_score: float
    final_score: float


class AIMemoryRankingEngine:
    """Ranks retrieval candidates with semantic + hybrid + recency boosting."""

    @staticmethod
    def _recency_score(created_at: datetime) -> float:
        now = datetime.now(timezone.utc)
        age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
        # Smooth decay where fresh memories receive higher score.
        return 1.0 / (1.0 + (age_days / 7.0))

    def rank(
        self,
        *,
        candidates: list[RetrievalCandidate],
        keyword_scores: dict,
        recency_boost_weight: float,
    ) -> list[RankedCandidate]:
        ranked: list[RankedCandidate] = []
        for item in candidates:
            hybrid_score = float(keyword_scores.get(item.chunk_id, 0.0))
            recency_score = self._recency_score(item.created_at)
            final_score = (
                (item.semantic_score * (1.0 - recency_boost_weight))
                + (hybrid_score * 0.20)
                + (recency_score * recency_boost_weight)
            )
            ranked.append(
                RankedCandidate(
                    candidate=item,
                    hybrid_score=hybrid_score,
                    recency_score=recency_score,
                    final_score=final_score,
                )
            )
        ranked.sort(key=lambda x: x.final_score, reverse=True)
        return ranked
