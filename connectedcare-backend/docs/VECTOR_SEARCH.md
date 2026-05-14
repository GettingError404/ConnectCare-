# Vector Search Architecture — ConnectedCare+

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Purpose

This document describes the implemented pgvector-backed semantic search path for AI memory chunks.

## Implemented Search Path

- `app/models/ai_memory.py` defines `AIMemoryEmbedding.embedding` as a 1536-dimensional pgvector column.
- `app/repositories/ai_memory.py` provides `semantic_search()` using cosine distance and tenant filtering.
- `app/workers/embedding_worker.py` generates embeddings and stores them through the repository.
- `alembic/versions/20260508_2100_add_ai_memory_persistence.py` creates the vector column and cosine index.

## Actual Behavior

1. A caller provides `tenant_id`, an embedding vector, a similarity threshold, and a limit.
2. The repository filters on `tenant_id` and excludes soft-deleted rows.
3. A pgvector cosine-distance query ranks matching chunks.
4. The repository returns chunk rows with similarity scores.

## Implemented Modules

- `app/repositories/ai_memory.py`
- `app/models/ai_memory.py`
- `app/workers/embedding_worker.py`
- `app/core/metrics.py` for search counters

## Limitations

- There is no separate vector store abstraction in the repository.
- There is no hybrid lexical retrieval layer.
- There is no orchestration or prompt-assembly pipeline.

## Future Work

- Add higher-level retrieval only if the codebase grows a real retrieval service.

## Which Modules This Documents

- `app/repositories/ai_memory.py`, `app/models/ai_memory.py`, `app/workers/embedding_worker.py`, `alembic/versions/20260508_2100_add_ai_memory_persistence.py`

## 17. Event-driven architecture flow

- Emit events for document indexed, index refreshed, vector deleted, and index stale.

## 18. Background worker architecture

- Workers chunk, embed, upsert, reindex, and delete vectors.

## 19. Embedding pipeline architecture

- Normalize, chunk, embed, verify metadata, and upsert atomically per batch.

## 20. AI observability architecture

- Track retrieval latency, index freshness, upsert failures, and cache hit rate.
