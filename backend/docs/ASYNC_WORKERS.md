# Async Workers — ConnectedCare+

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Purpose

Document the Celery-based background worker architecture for AI memory tasks (embeddings, summarization) with queue topology, retry strategy, tenant isolation, and idempotency.

## 1. Async Processing Architecture

### Responsibilities
- Move embedding generation, summarization, and batch processing out of request paths
- Guarantee retryable, observable, tenant-scoped task execution
- Implement idempotency via content hashing to prevent duplicate work
- Enforce tenant isolation and soft delete awareness in all worker operations

### Core Modules
- `app/core/celery_app.py` — Celery app factory, Redis broker/backend configuration, task signal instrumentation
- `app/workers/__init__.py` — queue topology (5 queues), retry strategy (exponential backoff, max 5 retries), base task classes
- `app/workers/embedding_worker.py` — embedding generation and storage (1536-dim vectors, pgvector)
- `app/workers/summarization_worker.py` — conversation window compression and summary storage
- `app/services/ai_memory_task_service.py` — high-level API for enqueueing tasks with priority routing

### Data Flow
1. API endpoint or service calls `AIMemoryTaskService.enqueue_*()` methods
2. Task is serialized (JSON) and sent to appropriate queue (embedding, summarization, memory, etc.)
3. Worker reserves task from queue, validates tenant scope
4. Worker performs work with idempotent side effects (content_hash deduplication)
5. Result persisted to PostgreSQL, metrics incremented
6. On failure: rerouted to retry queue with exponential backoff or dead-letter queue on max retries

### Queue Topology

**5 Queues:**
- **embedding** (priority=10, TTL=24h) — critical path, highest priority
  - Tasks: `generate_chunk_embedding()` — single chunk embedding
  - Max workers: scale to SLA (e.g., 4-8 workers for <1min p95 latency)
- **summarization** (priority=8, TTL=24h) — important, high priority
  - Tasks: `summarize_conversation_window()` — compress message window
  - Max workers: scale to SLA (e.g., 2-4 workers for <5min p95 latency)
- **memory** (priority=5, TTL=24h) — background batch operations
  - Tasks: `generate_conversation_embeddings()`, `schedule_periodic_summarization()` — batch enqueue children
  - Max workers: 1-2 (batcher queue)
- **retry** (priority=1, TTL=24h) — exponential backoff queue for failed tasks
  - Auto-routing destination for tasks exceeding error thresholds
  - Backoff: 1s → 2s → 4s → 8s → 16s (5 retries total)
  - Max workers: 1-2 (requeue only)
- **dead_letter** (priority=0, TTL=7d) — permanent failures (max retries exceeded)
  - Requires manual inspection and remediation
  - Max workers: 0 (dead-letter only, no consumers)

### Retry Strategy

**Configuration:**
```python
RETRY_BACKOFF_BASE = 1  # second
RETRY_MAX_RETRIES = 5   # exponential backoff: 1s, 2s, 4s, 8s, 16s
RETRY_BACKOFF_MAX = 600 # 10 minutes max backoff
```

**Flow:**
- Task raised exception on attempt 1 → requeue to `retry` queue with ETA = now + 1s
- Task raised exception on attempt 2 → requeue to `retry` queue with ETA = now + 2s
- Task raised exception on attempt 3 → requeue to `retry` queue with ETA = now + 4s
- Task raised exception on attempt 4 → requeue to `retry` queue with ETA = now + 8s
- Task raised exception on attempt 5 → requeue to `retry` queue with ETA = now + 16s
- Task raised exception on attempt 6 → **move to dead_letter queue** (max_retries exceeded)

**Idempotency:**
- Embedding tasks check `content_hash` before regenerating (already_embedded status if hash matches)
- Summarization tasks check `summary_hash` before storing (hash-based dedup prevents duplicate compression)
- Both prevent duplicate DB writes even after retries

### Base Task Classes

**BaseAIMemoryTask (extends Celery Task):**
- Automatic DB session creation and cleanup via context manager
- Context var propagation: `tenant_id_ctx`, `user_id_ctx`, `trace_id_ctx` for structured logging
- Lifecycle hooks: `on_failure()`, `on_retry()`, `on_call()`
- Dead-letter routing on max_retries exceeded
- Structured logging with task metadata (name, id, attempt, args)

**TenantAwareTask (extends BaseAIMemoryTask):**
- Mandatory `tenant_id` parameter in execute signature
- Automatic tenant context setup for all downstream operations
- Tenant validation to prevent cross-tenant task execution

### Security Implications
- Worker payloads are JSON-serialized (no pickle) for safety
- All tasks require tenant_id and validate it before execution
- Tasks use read-only repositories (no raw SQL injection vector)
- Soft delete and tenant filters enforced at repository level
- Task results stored in Redis with TTL expiry (no long-lived sensitive state)

## 2. Folder Structure

```
app/
  core/
    celery_app.py           — app factory, signal instrumentation
  workers/
    __init__.py             — queue topology, base classes, setup
    embedding_worker.py     — embedding generation task
    summarization_worker.py — summarization task
  services/
    ai_memory_task_service.py — enqueue API
  models/
    ai_memory.py            — ORM models (7 tables)
  repositories/
    ai_memory.py            — data access with tenant/soft-delete awareness
```

## 3. Task Implementations

### EmbeddingTask (`app/workers/embedding_worker.py`)

**Signature:**
```python
@app.task(name="ai_memory.embedding.generate", queue="embedding", priority=10)
def generate_chunk_embedding(
    tenant_id: str,
    chunk_id: str,
    embedding_model: str,
    embedding_version: str
) -> dict:
```

**Logic:**
1. Load chunk via `AIMemoryRepository.get_chunk(tenant_id, chunk_id)`
2. Check existing embedding via `get_embedding()` with content_hash comparison
3. If exists + same hash → return `{"status": "already_embedded", ...}`
4. If exists + different hash → regenerate (content changed)
5. Generate vector via `_generate_embedding_vector(chunk_text)` [stub returns [0.0]*1536]
6. Store via `repository.store_embedding()` with `embedded_at=utcnow()`
7. Emit metric: `inc_ai_memory_embeddings_generated(embedding_model)`
8. Return `{"status": "success", "embedding_id": "...", "embedding_dimension": 1536}`

**Error Handling:**
- Chunk not found → log warning, no retry (idempotent task completed)
- Embedding model error → log error, retry via exponential backoff
- Database error → log error, retry via exponential backoff
- On max retries exceeded → move to dead_letter queue

**Batch Enqueue:**
```python
AIMemoryTaskService.enqueue_embeddings_for_conversation(
    tenant_id="...",
    conversation_id="...",
    embedding_model="text-embedding-3-small",
    embedding_version="1",
    priority=PRIORITY_NORMAL
)
```
→ Enqueues batch task to `memory` queue
→ Batch task fetches all chunks
→ Batch task enqueues individual `generate_chunk_embedding` tasks to `embedding` queue with `priority=PRIORITY_HIGH-1`

### SummarizationTask (`app/workers/summarization_worker.py`)

**Signature:**
```python
@app.task(name="ai_memory.summarization.generate", queue="summarization", priority=8)
def summarize_conversation_window(
    tenant_id: str,
    conversation_id: str,
    window_start_at: str,  # ISO format
    window_end_at: str,    # ISO format
    summary_version: str
) -> dict:
```

**Logic:**
1. Load conversation via `AIMemoryRepository.get_conversation(tenant_id, conversation_id)`
2. Get messages in time window via `get_recent_messages()` then filter by `recorded_at`
3. Check for duplicate summary via `summary_hash` (idempotency)
4. Generate summary_text + summary_hash via `_generate_summary(windowed_messages)` [stub concatenates content + SHA256]
5. Store via `repository.create_summary()` with `source_window_start_at/end_at`
6. Emit metric: `inc_ai_memory_summaries_generated()`
7. Return `{"status": "success", "summary_id": "...", "message_count": len(messages)}`

**Error Handling:**
- Conversation not found → log warning, no retry
- No messages in window → log info, no retry (edge case, not an error)
- Database error → log error, retry via exponential backoff

**Batch Enqueue:**
```python
AIMemoryTaskService.enqueue_periodic_summarization(
    tenant_id="...",
    conversation_id="...",
    window_size_minutes=60,
    priority=PRIORITY_LOW
)
```
→ Enqueues batch task to `memory` queue
→ Batch task divides conversation into time windows
→ Batch task enqueues individual `summarize_conversation_window` tasks to `summarization` queue with `priority=PRIORITY_NORMAL`

## 4. Task Service API (`app/services/ai_memory_task_service.py`)

**Priority Constants:**
- `PRIORITY_CRITICAL = 10` — urgent, immediate processing
- `PRIORITY_HIGH = 8` — important, prioritized over background work
- `PRIORITY_NORMAL = 5` — regular background processing
- `PRIORITY_LOW = 1` — batch maintenance, lowest priority

**Methods:**
- `enqueue_embedding_for_chunk(tenant_id, chunk_id, embedding_model, embedding_version, priority=PRIORITY_HIGH)`
  - Routes to `embedding` queue
- `enqueue_embeddings_for_conversation(tenant_id, conversation_id, embedding_model, embedding_version, priority=PRIORITY_NORMAL)`
  - Routes batch task to `memory` queue → individual tasks to `embedding` queue
- `enqueue_summary_for_window(tenant_id, conversation_id, window_start_at, window_end_at, summary_version, priority=PRIORITY_NORMAL)`
  - Routes to `summarization` queue
- `enqueue_periodic_summarization(tenant_id, conversation_id, window_size_minutes, priority=PRIORITY_LOW)`
  - Routes batch task to `memory` queue → individual tasks to `summarization` queue
- `get_task_status(task_id)`
  - Returns `{"task_id", "status": "SUCCESS|PENDING|FAILURE", "result", "error"}`

## 5. Metrics & Observability

**AI Memory Metrics (incremented by workers):**
- `cc_ai_memory_embeddings_generated_total[embedding_model]` — counter
- `cc_ai_memory_embeddings_failed_total[embedding_model]` — counter
- `cc_ai_memory_summaries_generated_total` — counter
- `cc_ai_memory_summaries_failed_total` — counter
- `cc_ai_memory_chunks_created_total[chunk_type]` — counter
- `cc_ai_memory_searches_total[tenant]` — counter

**Celery Task Metrics (from `app/core/celery_app.py` signals):**
- Per-task counters: started, succeeded, failed, retried
- Task duration histogram (p50, p95, p99 latency)
- Queue depth (messages waiting) monitored via Celery events or Flower

**Structured Logging:**
- All worker log entries include: `task_id`, `task_name`, `tenant_id`, `trace_id`, `attempt`, `status`
- Failures include: `error`, `exception_type`, `traceback`
- Context vars (`tenant_id_ctx`, `user_id_ctx`, `trace_id_ctx`) propagated via middleware → workers

## 6. Tenant Isolation Strategy

**Enforcement Points:**
1. Task envelope must include `tenant_id` parameter (mandatory)
2. Task execution validates tenant_id before any DB access
3. All repository methods require tenant_id and filter by it
4. Soft delete filters applied: `WHERE deleted_at IS NULL AND tenant_id = ?`
5. Cross-tenant task execution impossible (tenant validation at worker entry)

**Example:**
```python
def execute_tenant_aware(db, tenant_id, chunk_id, ...):
    # tenant_id extracted from task payload
    chunk = repo.get_chunk(tenant_id, chunk_id)  # Mandatory tenant filter
    # No chunk from another tenant can be retrieved
```

## 7. Scaling Considerations

**Horizontal Scaling:**
- `embedding` queue: scale workers to maintain <1min p95 latency (4-8 workers typical)
- `summarization` queue: scale workers to maintain <5min p95 latency (2-4 workers typical)
- `memory` queue: 1-2 workers (batch/coordinator role)
- `retry` queue: 1 worker (requeue only, backoff handled by Redis/Celery)
- Monitor queue depth via `celery inspect active`, `celery inspect reserved`, or Flower dashboard

**Resource Constraints:**
- Each embedding task: 5min soft_time_limit, 10min hard_time_limit
- Each summarization task: 10min soft_time_limit, 15min hard_time_limit
- Database connections: default pool 5 + overflow 10 (shared across workers)
- Redis connections: minimal (Celery broker only, not result backend)

## 8. Development & Testing

**Local Setup:**
```bash
# Start Redis (required for broker/backend)
redis-server

# Start Celery worker (in separate terminal)
celery -A app.core.celery_app worker -l info -Q embedding,summarization,memory,retry

# View logs
tail -f celery.log
```

**Testing:**
- Unit tests in `tests/test_ai_memory_workers.py` mock repositories and validate task logic
- Integration tests use fixtures from `tests/conftest.py` (shared fixtures)
- Use `eager=True` in tests to execute tasks synchronously

## 9. Production Deployment

**Requirements:**
- Redis 6.0+ (Celery broker/result backend)
- PostgreSQL 14+ with pgvector 0.4.2 extension
- Celery workers running on separate compute nodes or containers
- Prometheus scrape job pointing to worker metrics endpoint (if using standalone metrics server)

**Health Checks:**
- Monitor Celery worker availability: `celery -A app.core.celery_app inspect active_queues`
- Monitor queue depth: `celery -A app.core.celery_app inspect stats | grep messages`
- Monitor dead-letter queue: regular inspection + alerting on non-zero depth

**Monitoring & Alerting:**
- Alert on task failure rate > 1% (per queue)
- Alert on queue depth > 100 (per queue)
- Alert on worker unavailability (all workers down)
- Dashboard: task latency (p95, p99), success rate, queue depth, worker count

## Why This Document Matters

This document gives operators and developers:
- Exact queue topology and retry strategy
- How to scale workers horizontally
- Tenant isolation mechanisms
- Idempotency and deduplication logic
- Observability metrics and logging patterns

## Which Modules This Documents

- **Celery infrastructure:** `app/core/celery_app.py`
- **Worker tasks:** `app/workers/embedding_worker.py`, `app/workers/summarization_worker.py`, `app/workers/__init__.py`
- **Task service:** `app/services/ai_memory_task_service.py`
- **Data access:** `app/repositories/ai_memory.py`
- **Metrics:** `app/core/metrics.py` (AI memory counters)
- **Tests:** `tests/test_ai_memory_workers.py`
