# Async AI Memory Processing Layer Implementation

## Overview

Production-grade async worker infrastructure for AI memory operations using Celery + Redis. Implements queue topology, embedding/summarization workers, retry handling, dead-letter routing, and observability without any agents, orchestration, or LLM integration.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Application Layer (Services/Routers)                             │
│ - Uses AIMemoryTaskService to enqueue tasks                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────────┐
│ Task Service Layer (app/services/ai_memory_task_service.py)     │
│ - High-level API for enqueueing embedding/summarization tasks    │
│ - Handles priority routing and result tracking                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────────┐
│ Redis Queue Topology                                             │
│ ┌──────────────┬──────────────┬──────────────┬────────┬────────┐ │
│ │ embedding    │ summarization│ memory       │ retry  │ dlq    │ │
│ │ (priority 10)│ (priority 8) │ (priority 5) │ (p: 1) │        │ │
│ └──────────────┴──────────────┴──────────────┴────────┴────────┘ │
│      TTL: none    TTL: none       TTL: none    24h     7d       │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────────┐
│ Celery Workers (distributed, multi-process safe)                │
│ ┌─────────────────────────┐  ┌──────────────────────────────┐   │
│ │ EmbeddingTask           │  │ SummarizationTask            │   │
│ │ - Max retries: 5        │  │ - Max retries: 5            │   │
│ │ - Soft limit: 5m        │  │ - Soft limit: 10m           │   │
│ │ - Hard limit: 10m       │  │ - Hard limit: 15m           │   │
│ │ - Idempotent via hash   │  │ - Idempotent via hash       │   │
│ │ - Tenant-aware          │  │ - Tenant-aware              │   │
│ │ - Dead-letter on fail   │  │ - Dead-letter on fail       │   │
│ └─────────────────────────┘  └──────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────────┐
│ Data Layer (Repository + ORM)                                    │
│ - AIMemoryRepository for safe, tenant-aware queries              │
│ - Vector storage with pgvector                                   │
│ - Structured logging + metrics emission                          │
└─────────────────────────────────────────────────────────────────┘
```

## Queue Topology

```
Queue         | Priority | Exchange   | Routing Key      | TTL
--------------|----------|------------|------------------|----------
embedding     | 10       | ai_memory  | embedding        | None
summarization | 8        | ai_memory  | summarization    | None
memory        | 5        | ai_memory  | memory           | None
retry         | 1        | ai_memory  | retry            | 24 hours
dead_letter   | -        | ai_memory  | dead_letter      | 7 days
```

**Priority Semantics:**
- Higher priority (10) = processed sooner
- Embedding highest: time-sensitive vector generation
- Summarization high: important for memory compression
- Memory normal: background chunk/link operations
- Retry low: already failed once, backoff appropriate
- Dead-letter: no priority, manual intervention needed

## Files Created

### 1. app/workers/__init__.py (380 lines)

**Queue Topology:**
- `QueueName` enum: EMBEDDING, SUMMARIZATION, MEMORY, RETRY, DEAD_LETTER
- `QueueConfig`: Kombu queue configuration with max-priority and TTL
- `setup_ai_memory_queues()`: Initialize topology on Celery app

**Retry Strategy:**
- `RetryConfig`: Exponential backoff (1s, 2s, 4s, 8s, 16s..., max 10m)
- Max retries: 5
- Autoretry on any Exception

**Base Worker Classes:**
- `BaseAIMemoryTask(Task)`: Abstract base with lifecycle hooks
  - Automatic DB session + cleanup
  - Context var propagation (tenant_id, user_id, trace_id)
  - Structured logging with task metadata
  - Dead-letter routing on final failure
  - `on_failure()` hook: final failure handling
  - `on_retry()` hook: retry tracking

- `TenantAwareTask(BaseAIMemoryTask)`: Base for tenant-scoped tasks
  - Mandatory tenant_id parameter
  - Automatic tenant context setup

### 2. app/workers/embedding_worker.py (260 lines)

**Task: EmbeddingTask**
- Queue: `embedding` (priority 10)
- Soft limit: 5 min, Hard limit: 10 min
- Max retries: 5

**Lifecycle:**
1. Load chunk from repository
2. Check for existing embedding (idempotency)
3. Skip if hash unchanged (re-embed detection)
4. Generate embedding vector (stub placeholder)
5. Store in database
6. Emit metrics

**Idempotency:**
- Deduplication via chunk_id + embedding_model
- Content hash change triggers re-embedding
- Prevents duplicate vector storage

**Celery Tasks:**
- `generate_chunk_embedding(tenant_id, chunk_id)`: Single chunk
- `generate_conversation_embeddings(tenant_id, conversation_id)`: Batch (enqueues individual tasks)

**Metrics:**
- `inc_ai_memory_embeddings_generated(model)`
- `inc_ai_memory_embeddings_failed(model)`

### 3. app/workers/summarization_worker.py (320 lines)

**Task: SummarizationTask**
- Queue: `summarization` (priority 8)
- Soft limit: 10 min, Hard limit: 15 min
- Max retries: 5

**Lifecycle:**
1. Load conversation
2. Get messages in time window
3. Check for duplicate summary (idempotency)
4. Generate summary text + hash (stub placeholder)
5. Store summary
6. Emit metrics

**Idempotency:**
- Deduplication via summary_hash
- Summary version tracking for re-summarization
- Prevents duplicate compression

**Celery Tasks:**
- `summarize_conversation_window(tenant_id, conversation_id, window_start_at, window_end_at)`: Single window
- `schedule_periodic_summarization(tenant_id, conversation_id, window_size_minutes)`: Batch (enqueues window tasks)

**Metrics:**
- `inc_ai_memory_summaries_generated()`
- `inc_ai_memory_summaries_failed()`

### 4. app/tasks/ai_memory_tasks.py (20 lines)

Re-exports worker tasks for external consumption:
- `generate_chunk_embedding`
- `generate_conversation_embeddings`
- `summarize_conversation_window`
- `schedule_periodic_summarization`

### 5. app/services/ai_memory_task_service.py (210 lines)

**High-level Task Enqueueing API:**

```python
# Single operations
task_id = AIMemoryTaskService.enqueue_embedding_for_chunk(
    tenant_id, chunk_id, priority=HIGH
)

task_id = AIMemoryTaskService.enqueue_summary_for_window(
    tenant_id, conversation_id, window_start, window_end
)

# Batch operations
task_id = AIMemoryTaskService.enqueue_embeddings_for_conversation(
    tenant_id, conversation_id
)

task_id = AIMemoryTaskService.enqueue_periodic_summarization(
    tenant_id, conversation_id, window_size_minutes=60
)

# Status tracking
status = AIMemoryTaskService.get_task_status(task_id)
# Returns: {"task_id": "...", "status": "SUCCESS|PENDING|FAILURE", "result": {...}, "error": None}
```

**Priority Constants:**
- `PRIORITY_CRITICAL` = 10 (urgent)
- `PRIORITY_HIGH` = 8
- `PRIORITY_NORMAL` = 5 (default)
- `PRIORITY_LOW` = 1 (background)

### 6. app/core/metrics.py (additions)

**New Metrics:**
```
cc_ai_memory_embeddings_generated_total{embedding_model}
cc_ai_memory_embeddings_failed_total{embedding_model}
cc_ai_memory_summaries_generated_total
cc_ai_memory_summaries_failed_total
cc_ai_memory_chunks_created_total{chunk_type}
cc_ai_memory_searches_total{tenant}
```

**New Functions:**
- `inc_ai_memory_embeddings_generated(embedding_model)`
- `inc_ai_memory_embeddings_failed(embedding_model)`
- `inc_ai_memory_summaries_generated()`
- `inc_ai_memory_summaries_failed()`
- `inc_ai_memory_chunks_created(chunk_type)`
- `inc_ai_memory_searches(tenant)`

### 7. tests/test_ai_memory_workers.py (500 lines)

**Test Classes:**
- `TestQueueTopology`: Queue names, retry config, autoretry structure
- `TestEmbeddingWorker`: Success, idempotency, error handling
- `TestSummarizationWorker`: Generation, window handling, duplication
- `TestAIMemoryTaskService`: Enqueue API, priority routing, queue selection
- `TestTenantIsolation`: Tenant filtering on chunk/conversation queries
- `TestErrorHandling`: Graceful degradation, no spurious retries

**Coverage:** 30+ test methods, ~200 assertions

## Production Features

### Retry + Backoff
```python
Attempt 1: Immediate
Attempt 2: 1 second backoff
Attempt 3: 2 second backoff
Attempt 4: 4 second backoff
Attempt 5: 8 second backoff
After 5: Dead-letter + critical alert
```

**Exponential backoff prevents thundering herd on transient failures.**

### Dead-Letter Queue
- Final failure routes to `dead_letter` queue (TTL: 7 days)
- Manual inspection possible via monitoring/alerting
- Includes task args, kwargs, exception in log record
- Critical severity logging for DLQ events

### Tenant Isolation
- Every task receives tenant_id as parameter
- Repository queries enforce `WHERE tenant_id = ?`
- Cross-tenant data access impossible via workers
- Tenant context var set for structured logging

### Idempotency
- **Embedding:** Via chunk_id + embedding_model + content_hash
  - Same content = skip generation
  - Different content = regenerate
  
- **Summarization:** Via summary_hash + version tracking
  - Duplicate hash = skip storage
  - New hash = store and link

**Prevents duplicate vector storage and redundant summaries.**

### Observability

**Metrics:**
- Embeddings: model-tagged counters (success, failure)
- Summaries: counters (success, failure)
- Chunks: type-tagged counters
- Searches: tenant-tagged counters

**Logging:**
- `task_start`: Task initiated with tenant_id
- `task_retry`: Retry attempt with retry count
- `task_final_failure`: Final failure after max retries
- `task_dead_lettered`: Critical alert for DLQ routing
- Structured JSON with request_id, tenant_id, trace_id

**Time Limits:**
- Soft limit: Graceful SigTerm, task can cleanup
- Hard limit: SigKill, task force-terminated
- Prevents runaway tasks consuming resources

### Queue Isolation

```
Real-time operations → embedding queue (priority 10)
Significant ops → summarization queue (priority 8)
Background ops → memory queue (priority 5)
Retry backoffs → retry queue (priority 1)
Failed tasks → dead_letter queue (manual)
```

**Prevents resource starvation; high-priority work isn't blocked by low-priority background jobs.**

## Configuration

### Celery Configuration (existing, used as-is)

```python
# app/core/celery_app.py
celery_app = make_celery(
    broker="redis://...",  # CELERY_BROKER_URL env var
    backend="redis://...",  # CELERY_RESULT_BACKEND env var
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
    task_track_started=True,
)
```

### Queue Initialization

```python
# In app startup (e.g., main.py or router)
from app.workers import setup_ai_memory_queues
setup_ai_memory_queues()
```

### Worker Launch

```bash
# Single worker consuming all AI memory queues
celery -A app.core.celery_app worker --queues=embedding,summarization,memory,retry,dead_letter -l info

# Or separate worker processes for queue isolation
celery -A app.core.celery_app worker --queues=embedding -c 4 -l info  # 4 processes for embedding
celery -A app.core.celery_app worker --queues=summarization -c 2 -l info  # 2 for summarization
celery -A app.core.celery_app worker --queues=memory,retry -c 2 -l info  # 2 for memory ops
```

### Environment Variables

```bash
# Required for Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Optional, for multiprocess metrics
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_metrics
```

## Usage Examples

### Embed a Single Chunk

```python
from app.services.ai_memory_task_service import AIMemoryTaskService
from uuid import UUID

task_id = AIMemoryTaskService.enqueue_embedding_for_chunk(
    tenant_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
    chunk_id=UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
    priority=AIMemoryTaskService.PRIORITY_HIGH
)
print(f"Embedding queued: {task_id}")

# Check status later
status = AIMemoryTaskService.get_task_status(task_id)
print(status)  # {"status": "SUCCESS", "result": {...}}
```

### Bulk Embed Conversation

```python
task_id = AIMemoryTaskService.enqueue_embeddings_for_conversation(
    tenant_id=tenant_uuid,
    conversation_id=conversation_uuid,
    priority=AIMemoryTaskService.PRIORITY_NORMAL
)
# This enqueues one task that fetches all chunks and enqueues individual embedding tasks
```

### Summarize Time Window

```python
from datetime import datetime, timedelta

window_start = datetime.utcnow() - timedelta(hours=1)
window_end = datetime.utcnow()

task_id = AIMemoryTaskService.enqueue_summary_for_window(
    tenant_id=tenant_uuid,
    conversation_id=conversation_uuid,
    window_start_at=window_start,
    window_end_at=window_end,
    priority=AIMemoryTaskService.PRIORITY_NORMAL
)
```

### Batch Summarize Entire Conversation

```python
task_id = AIMemoryTaskService.enqueue_periodic_summarization(
    tenant_id=tenant_uuid,
    conversation_id=conversation_uuid,
    window_size_minutes=30,  # 30-minute windows
    priority=AIMemoryTaskService.PRIORITY_LOW  # Background job
)
```

## What's NOT Implemented (By Design)

✗ Agents (user explicitly disallowed)
✗ Orchestration (user explicitly disallowed)
✗ Prompt assembly (user explicitly disallowed)
✗ OpenAI chat flows (user explicitly disallowed)
✗ Routers/API endpoints (user explicitly disallowed)
✗ Actual LLM calls (embeddings and summaries are placeholder stubs)
✗ Real vector generation (returns correct dimension of zeros)

**This is strictly the async infrastructure layer. Actual AI logic is out-of-scope.**

## Validation

### Syntax & Imports
```
✓ app/workers/__init__.py - No errors
✓ app/workers/embedding_worker.py - No errors
✓ app/workers/summarization_worker.py - No errors
✓ app/tasks/ai_memory_tasks.py - No errors
✓ app/services/ai_memory_task_service.py - No errors
✓ app/core/metrics.py - No errors
✓ tests/test_ai_memory_workers.py - No errors
```

### Module Imports
```
✓ Worker base classes import successfully
✓ Worker tasks import successfully
✓ Task service import successfully
✓ Metrics functions import successfully
```

### Test Coverage
- Queue topology (names, config, routing)
- Embedding worker (success, idempotency, error handling)
- Summarization worker (generation, windows, deduplication)
- Task service (enqueueing, priority, status)
- Tenant isolation (queries respect tenant_id)
- Error handling (graceful degradation, no spurious retries)

## Monitoring & Alerting

### Key Metrics to Monitor

```
cc_ai_memory_embeddings_generated_total  # Should be increasing
cc_ai_memory_embeddings_failed_total      # Should be low
cc_ai_memory_summaries_generated_total    # Should be increasing
cc_ai_memory_summaries_failed_total       # Should be low
cc_celery_task_retries_total{task_name}  # Spike = transient issues
cc_celery_task_failures_total{task_name} # Should be low
```

### Alert Rules

```
- Embedding failure rate > 5% → PagerDuty P2
- Summary generation failure → PagerDuty P3
- Task in retry queue > 1 hour → investigate
- Dead-letter queue non-empty → manual triage required
```

### Logs to Tail

```bash
# Watch embedding tasks
docker logs celery-worker | grep embedding_stored

# Watch failures
docker logs celery-worker | grep task_final_failure

# Watch dead-letter routing
docker logs celery-worker | grep task_dead_lettered
```

## Next Steps (Out of Scope)

- Actual LLM integration (OpenAI embedding API, summarization models)
- Prompt engineering and template system
- Agent-based task orchestration
- REST/WebSocket APIs for real-time worker monitoring
- Distributed tracing (Jaeger, Datadog)
- Queue prioritization tuning (may need adjustment post-deployment)
