from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.repositories.ai_memory_intelligence_async import RetrievalCandidate
from app.services.ai_memory.ranking_engine import AIMemoryRankingEngine
from app.services.embeddings.chunking import TokenSafeChunker


def test_token_safe_chunker_overlap_behavior():
    text = " ".join([f"w{i}" for i in range(20)])
    chunker = TokenSafeChunker(chunk_size_tokens=8, overlap_tokens=2)
    chunks = chunker.chunk_text(text)

    assert len(chunks) >= 3
    first = chunks[0].split()
    second = chunks[1].split()
    # Expect 2-token overlap between contiguous chunks.
    assert first[-2:] == second[:2]


def test_ranking_engine_applies_recency_boost():
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=60)

    candidates = [
        RetrievalCandidate(
            memory_id=uuid4(),
            chunk_id=uuid4(),
            chunk_text="old but semantically good",
            memory_type="long_term",
            source_type="document",
            created_at=old,
            semantic_score=0.90,
            metadata=None,
        ),
        RetrievalCandidate(
            memory_id=uuid4(),
            chunk_id=uuid4(),
            chunk_text="new and relevant",
            memory_type="short_term",
            source_type="conversation",
            created_at=now,
            semantic_score=0.85,
            metadata=None,
        ),
    ]

    engine = AIMemoryRankingEngine()
    ranked = engine.rank(candidates=candidates, keyword_scores={}, recency_boost_weight=0.4)

    assert len(ranked) == 2
    assert ranked[0].candidate.created_at >= ranked[1].candidate.created_at


def test_chunker_rejects_invalid_overlap():
    try:
        TokenSafeChunker(chunk_size_tokens=100, overlap_tokens=100)
        assert False, "Expected ValueError for invalid overlap"
    except ValueError:
        assert True
