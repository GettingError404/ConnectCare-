# Observability — Logging, Metrics, Tracing

STATUS: IMPLEMENTED
Last verified against repository state: 2026-05-09

Purpose

Document the current observability stack (structured logging + Prometheus metrics) and how to extend it safely.

Logging

- Structured JSON logs: configured in `app/core/logging.py` and used across the app.
  - Context fields: `service`, `request_id`, `tenant_id`, `user_id`, `trace_id` (populated via `logging_middleware` and `tenant_context` middleware).
  - Avoid adding high-cardinality fields to `extra`.

Metrics

- Prometheus instrumentation lives in `app/core/metrics.py`.
- Metrics exported at `/metrics` endpoint: counters, histograms, gauges tracked by labels (tenant, endpoint, method, status, etc.)
- Supported multiprocess mode via `PROMETHEUS_MULTIPROC_DIR` (for multiple worker processes)

**HTTP/Request Metrics:**
- `cc_http_requests_total` (counter) — total HTTP requests by route, method, status
- `cc_http_request_duration_seconds` (histogram) — request latency distribution (labels: endpoint, method)

**Telemetry Metrics:**
- `cc_mqtt_messages_total` (counter) — MQTT messages received
- `cc_ingest_events_total` (counter) — events persisted (labels: event_type)
- `cc_alerts_triggered_total` (counter) — alert events fired

**AI Memory Metrics** (NEW):
- `cc_ai_memory_embeddings_generated_total` (counter) — embeddings successfully generated (labels: embedding_model)
- `cc_ai_memory_embeddings_failed_total` (counter) — embedding generation failures (labels: embedding_model)
- `cc_ai_memory_summaries_generated_total` (counter) — conversation summaries successfully created
- `cc_ai_memory_summaries_failed_total` (counter) — summary generation failures
- `cc_ai_memory_chunks_created_total` (counter) — chunks extracted from messages/summaries (labels: chunk_type)
- `cc_ai_memory_searches_total` (counter) — semantic search queries executed (labels: tenant)

**Celery Task Metrics:**
- Task lifecycle: prerun, postrun, failure, retry signals instrumented in `app.core.celery_app`
- Per-task counters and histograms for duration, retry count, failure rate

**WebSocket Metrics:**
- Connected clients, messages sent, connection/disconnection events

**Event Bus Metrics:**
- Redis pub/sub message throughput by channel

Tracing (preparation)

- Current code sets `trace_id` contextvar and logs it.
- OpenTelemetry instrumentation is not enabled yet — the code is prepared to accept trace id propagation (headers like `traceparent` are read by `logging_middleware`).

Dashboards and recording rules (recommendations)

Build Grafana dashboards around:

**Operational Dashboard:**
- Request latency per route (p95, p99)
- Per-tenant request volume (top 10 tenants by request count)
- Ingest throughput & duplicate rates (MQTT → persisted)
- Alert triggers, cooldowns, escalations

**AI Memory Dashboard:**
- Embedding generation rate and latency (histogram p50, p95, p99 by model)
- Summary generation success/failure rate (by conversation_id patterns)
- Semantic search query rate and latency (by tenant)
- Chunk extraction volume by chunk_type
- Vector database query performance (IVFFlat index overhead)

**Celery/Worker Dashboard:**
- Task queue depth (messages in embedding/summarization/retry/dead_letter queues)
- Task success/failure/retry rates (by queue and task name)
- Task duration distribution (histogram)
- Worker availability and uptime

**System Health:**
- Database connection pool utilization
- Redis connection pool utilization
- WebSocket client count
- Error rates and 5xx responses

Best practices & anti-patterns

- DO: use route-template as endpoint label, include `tenant` as label only if tenant cardinality is controlled.
- DO NOT: add `user_id`, `device_id`, or other high-cardinality identifiers as metric labels.

Debugging tips

- If metrics missing with multiple workers, ensure `PROMETHEUS_MULTIPROC_DIR` is set and writable.
- Use `curl /metrics` on a single worker instance to confirm metrics are exposed before adding multiprocess complexity.

Why this document matters

Observability is essential to run the system in production — this doc gives on-call engineers the exact locations of logs and metrics and operational pitfalls.

Which modules this documents

- **Logging:** `app/core/logging.py`, `app/middleware/logging_middleware.py`
- **Metrics:** `app/core/metrics.py`, `app/middleware/metrics_middleware.py`
- **Celery/Task instrumentation:** `app/core/celery_app.py`, `app/workers/*`
- **AI Memory metrics:** metrics counters in `app/core/metrics.py` and incremented by `app/workers/embedding_worker.py`, `app/workers/summarization_worker.py`
