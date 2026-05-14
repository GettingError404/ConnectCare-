# AI System Architecture — ConnectedCare+

Purpose

This document defines the production architecture for the upcoming AI Memory + Agent platform. It is a design contract for how AI services will be organized, secured, observed, and scaled inside the existing ConnectedCare+ backend.

## 1. System architecture

### Responsibilities
- Provide a secure, tenant-aware AI runtime for memory, retrieval, planning, and agent execution.
- Keep AI-specific concerns isolated from the existing clinical API, ingestion, alerting, and auth subsystems.
- Support synchronous chat-style requests and asynchronous background agent jobs.

### Modules
- `app/ai/api` — AI-facing HTTP endpoints and WebSocket/stream adapters.
- `app/ai/orchestration` — agent planning, tool selection, workflow state machine.
- `app/ai/memory` — short-term state, long-term memory, summarization, expiry.
- `app/ai/retrieval` — embedding lookup, hybrid retrieval, reranking, context assembly.
- `app/ai/embeddings` — embedding jobs, batching, backpressure, model selection.
- `app/ai/vectorstores` — vector DB access layer, namespace isolation, lifecycle.
- `app/ai/workers` — async tasks for indexing, summarization, and maintenance.
- `app/ai/observability` — traces, metrics, token accounting, prompt audit logs.

### Interfaces
- HTTP: authenticated AI session APIs for conversation, memory, and agent execution.
- Async jobs: queue-based worker contracts for embedding, ingestion, and summarization.
- Internal service APIs: repository-style interfaces for memory, retrieval, and execution state.

### Data flow
1. Client issues an AI request with tenant-scoped identity and a conversation or task reference.
2. The orchestration layer resolves policy, retrieves relevant memory, and assembles context.
3. The agent planner decides whether to answer directly, retrieve more data, or schedule async work.
4. The response is returned with audit metadata, token usage, and trace identifiers.

### Async boundaries
- Heavy or slow operations must not block request threads: embedding, summarization, and background retrieval run in workers.
- Agent plans that require external tool calls should be represented as stateful jobs with resumable checkpoints.

### Caching strategy
- Cache tenant-safe retrieval results, policy lookups, and recent conversation state.
- Cache embeddings by content hash to avoid duplicate vector writes.
- Cache prompt templates and tool metadata with short TTLs.

### Scaling considerations
- Horizontal scale for API, retrieval, and worker pools.
- Partition vector indexes by tenant and domain to reduce fan-out.
- Keep orchestration stateless except for persisted run state.

### Security implications
- All AI operations must be tenant-bound and authorization-checked before retrieval or memory access.
- Prompt, memory, and tool outputs are treated as untrusted inputs and must be sanitized before use.
- AI services must never bypass RBAC, tenant isolation, or healthcare audit requirements.

## 2. Folder structure

Recommended AI-specific structure to coexist with the current backend:

- `app/ai/api` — public AI routes and stream handlers
- `app/ai/orchestration` — plan execution, tool routing, guards, policies
- `app/ai/memory` — memory models, lifecycle rules, summarizers
- `app/ai/retrieval` — retrieval pipeline, ranking, filters, query planning
- `app/ai/embeddings` — embedding jobs and batchers
- `app/ai/vectorstores` — vector database repositories and adapters
- `app/ai/workers` — Celery tasks for indexing and maintenance
- `app/ai/observability` — AI metrics, traces, prompt logs, audit utilities
- `app/ai/schemas` — request/response contracts
- `app/ai/services` — thin domain services coordinating the above modules

## 3. Service boundaries

- AI API service: validates request identity, rate limits, and request envelope.
- Orchestration service: owns plan selection, tool routing, and state transitions.
- Memory service: owns persistence, expiry, summarization, and recall policies.
- Retrieval service: owns query expansion, filtering, ranking, and reranking.
- Embedding service: owns batching, model selection, dedupe, and write-through to vector storage.
- Worker service: owns async execution, retries, and idempotent job processing.
- Observability service: owns metrics, traces, prompt logs, and AI audit artifacts.

## 4. Repository patterns

- Use repository interfaces for memory records, agent runs, retrieval artifacts, and vector documents.
- Keep repositories persistence-focused and free of prompt logic or policy decisions.
- Use tenant-scoped queries by default; no repository should expose cross-tenant read paths.
- Prefer idempotent write methods that accept content hashes, run ids, and dedupe keys.

## 5. Memory lifecycle design

- Ephemeral memory: request-local context and session scratchpad, discarded after run completion.
- Short-term memory: conversation turns and recent actions, retained for active sessions.
- Long-term memory: durable user/tenant preferences, summaries, approved insights, and embeddings.
- Expiration: memory entries carry retention class, last_accessed, and expires_at policies.
- Promotion: the summarization pipeline decides when a session artifact is promoted into durable memory.

## 6. AI orchestration flow

1. Validate tenant, user, role, and AI feature access.
2. Build a minimal request plan from the user intent and task metadata.
3. Retrieve policy, memory, and domain context.
4. Decide whether to answer, ask clarifying questions, or enqueue background work.
5. Execute tool calls with explicit guardrails.
6. Persist run state, audit events, and token accounting.

## 7. Retrieval architecture

- Retrieval should support hybrid search: vector similarity plus structured filters and keyword constraints.
- Retrieval must be tenant-scoped before any similarity ranking is applied.
- Candidate documents should be re-ranked by recency, trust level, source type, and task relevance.
- Retrieval results are cached with short TTLs and invalidated on memory or content updates.

## 8. Async processing architecture

- Use Celery for embedding, indexing, summarization, and deferred agent jobs.
- Async jobs must be resumable and idempotent by job id and content hash.
- Worker queues should be isolated by task class: critical, default, indexing, and low-priority maintenance.
- Retries should be bounded and include dead-letter handling for irrecoverable failures.

## 9. Vector database strategy

- Store vectors in a tenant-aware namespace strategy.
- Enforce soft-delete and hard-delete lifecycle controls for compliance and retention.
- Use metadata filters for tenant, user, document type, source trust, and retention class.
- Keep embedding dimension and model version explicit in metadata to support reindexing.

## 10. Context assembly pipeline

- Start from a compact request frame: user intent, policy, tenant, and recent session state.
- Add retrieved memory in ranked layers: session, user preference, tenant knowledge, and task evidence.
- Apply dedupe and compression before prompt construction.
- Emit token counts and context provenance for every assembled request.

## 11. Token budgeting strategy

- Reserve fixed tokens for system policy, safety instructions, and output formatting.
- Allocate dynamic budgets for memory, retrieval, tool output, and model response length.
- Use summarization and truncation when the context budget is exceeded.
- Record budget decisions as part of observability for tuning and audits.

## 12. Prompt injection architecture

- Treat retrieved text, tool outputs, and user-supplied content as untrusted.
- Separate system policy from user context with clear structural boundaries.
- Use policy filters to block instruction overrides, data exfiltration attempts, and cross-tenant leakage.
- Maintain a prompt audit trail with source attribution for every included segment.

## 13. Tenant isolation strategy

- Every query, memory read, retrieval request, and vector lookup must be tenant-qualified.
- Tenant context is derived from authenticated identity and validated against runtime policy.
- No fallback paths should default to global memory or cross-tenant search.
- Shared infrastructure is allowed, but all logical data access must remain tenant-partitioned.

## 14. Healthcare compliance considerations

- Minimize PHI exposure in prompts and logs.
- Redact sensitive values before persistence where possible.
- Keep traceability for access, retention, deletion, and audit.
- Support data retention policies by memory class and tenant policy.

## 15. Scalability planning

- Scale read-heavy retrieval independently from write-heavy ingestion.
- Scale workers independently from API nodes.
- Use queue partitioning and backpressure to prevent embedding storms.
- Prefer stateless orchestration so new AI workloads can be scaled horizontally.

## 16. Failure handling strategy

- If retrieval fails, degrade to direct answer or ask for clarification instead of hard failing.
- If vector DB is unavailable, queue indexing jobs and return a partial response with warning metadata.
- If token budget is exceeded, fall back to summarization before dropping entire context layers.
- Persist failure state for retry, replay, and incident analysis.

## 17. Event-driven architecture flow

- Domain events should be emitted for memory write, memory expiry, retrieval completion, tool execution, and agent completion.
- Events feed observability, async workers, and downstream system integrations.
- Event payloads must be tenant-scoped, versioned, and idempotent.

## 18. Background worker architecture

- Workers handle embedding, summarization, indexing, compaction, and batch maintenance.
- Worker code must be side-effect safe and able to resume after failure.
- Separate high-priority user-facing tasks from low-priority maintenance jobs.

## 19. Embedding pipeline architecture

- Normalize source content, chunk it, assign stable content hashes, and compute embeddings.
- Write vectors only after successful tenant validation and policy checks.
- Update index metadata with model version, source type, and retention class.
- Re-embedding should be queued when model versions change or content is updated.

## 20. AI observability architecture

- Observe request count, latency, queue depth, token usage, retrieval hit rate, and tool execution outcomes.
- Record prompt and context lineage for debugging and compliance.
- Capture agent plan transitions and background job lifecycle events.
- Link AI traces to request IDs, tenant IDs, and user IDs for incident response.
