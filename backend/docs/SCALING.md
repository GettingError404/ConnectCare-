# Scaling Plan — ConnectedCare+

STATUS: PLANNED (NOT IMPLEMENTED)
Last verified against repository state: 2026-05-09

Purpose

This document defines the scale-out strategy for the future AI platform and the infrastructure that supports it.

## 1. Scalability planning

### Responsibilities
- Preserve latency, correctness, and isolation as the AI workload grows.
- Separate compute-heavy AI flows from standard API traffic.

### Modules
- API tier, orchestration tier, retrieval tier, worker tier, vector tier, observability tier.

### Interfaces
- Stateless request APIs.
- Queue-based async jobs.
- Tenant-scoped repositories and caches.

### Data flow
- Requests remain small and synchronous where possible.
- Heavy work shifts to queues and workers.

### Async boundaries
- Any task that grows with content volume should be asynchronous by default.

### Caching strategy
- Use short-lived caches for retrieval, policy, and prompt templates.
- Keep tenant-specific cache keys to preserve isolation.

### Scaling considerations
- Horizontal scale for API and workers.
- Partition by tenant and workload class.
- Use backpressure to protect expensive systems.

### Security implications
- Scale must not weaken tenant isolation or PHI protection.

## 2. Folder structure

- `app/ai/*` for the new AI platform boundaries
- Existing `app/services`, `app/models`, and `app/repositories` remain the system-of-record for shared backend concerns

## 3. Service boundaries

- API service: request ingress and response composition.
- Retrieval service: read-heavy query processing.
- Worker service: heavy background execution.
- Vector service: index management and search.

## 4. Repository patterns

- Repositories should support batch operations, pagination, and tenant scoping.
- Avoid chatty persistence patterns.

## 5. Memory lifecycle design

- Older memory should be compacted or archived to reduce retrieval overhead.

## 6. AI orchestration flow

- Keep orchestration stateless; persist only the run state that is needed for recovery.

## 7. Retrieval architecture

- Limit candidate set sizes and rerank costs.

## 8. Async processing architecture

- Split queues by priority and domain.

## 9. Vector database strategy

- Use tenant partitions and versioned indexes to reduce reindex blast radius.

## 10. Context assembly pipeline

- Use deterministic budgets and bounded source counts.

## 11. Token budgeting strategy

- Reserve response headroom and compress source context aggressively when needed.

## 12. Prompt injection architecture

- Scaling must never remove policy gates or provenance checks.

## 13. Tenant isolation strategy

- Multi-tenant scaling requires logical partitioning even when physical infra is shared.

## 14. Healthcare compliance considerations

- Retention and deletion policies must remain enforceable at larger volumes.

## 15. Scalability planning

- Introduce per-tenant quotas, queue fairness, and backpressure policies.

## 16. Failure handling strategy

- Degrade gracefully under partial outages; do not cascade failures into the core API.

## 17. Event-driven architecture flow

- Use events to decouple write-side and read-side scalability.

## 18. Background worker architecture

- Scale workers independently by task type and customer demand.

## 19. Embedding pipeline architecture

- Batch and dedupe aggressively to control model cost and queue pressure.

## 20. AI observability architecture

- Track cost per tenant, latency by workload, queue depth, and saturation signals.

## Limitations

- This is a planning document; the repository does not implement the broader AI platform described here.

## Future Work

- Convert to an implemented scaling guide only if new platform layers are added.
