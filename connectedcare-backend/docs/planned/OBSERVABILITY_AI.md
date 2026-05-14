# AI Observability — ConnectedCare+

STATUS: PLANNED (NOT IMPLEMENTED)
Last verified against repository state: 2026-05-09

Purpose

This document defines observability requirements for AI workloads: traces, logs, metrics, audits, and operational dashboards.

## 1. AI observability architecture

### Responsibilities
- Provide operational visibility into AI requests, retrieval quality, tool execution, memory writes, and async jobs.
- Support compliance audits without leaking sensitive content.

### Modules
- `app/ai/observability/metrics` — counters, histograms, gauges.
- `app/ai/observability/tracing` — span names, attributes, and correlation.
- `app/ai/observability/logging` — structured prompt and run logs.
- `app/ai/observability/audit` — immutable audit trail helpers.

### Interfaces
- `AIMetrics.record_*` for usage and latency.
- `TraceContext` for request/tenant/run propagation.
- `AuditRecorder.record(event)` for compliance events.

### Data flow
1. Request enters with correlation metadata.
2. Orchestration, retrieval, and memory steps emit spans and metrics.
3. Tool calls emit structured audit events.
4. Completion writes final usage and outcome metadata.

### Async boundaries
- Heavy logging/export can be batched asynchronously.

### Caching strategy
- Metrics are accumulated in-memory and exported periodically.
- Avoid caching sensitive prompt text in long-lived stores.

### Scaling considerations
- High-cardinality labels must be controlled.
- Separate high-volume AI metrics from general API metrics where practical.
