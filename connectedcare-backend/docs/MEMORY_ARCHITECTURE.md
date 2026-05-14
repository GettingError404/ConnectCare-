# Memory Architecture — ConnectedCare+

Purpose

This document defines the memory model for the AI platform: how memory is written, retrieved, summarized, retained, and safely isolated in a multi-tenant healthcare environment.

## 1. Memory lifecycle design

### Responsibilities
- Maintain session, user, tenant, and task memory with explicit retention policies.
- Protect PHI through retention controls, redaction, and scoped access.
- Convert raw conversation history into durable, searchable memory only when policy allows.

### Modules
- `app/ai/memory/models` — memory entities, retention metadata, source attribution.
- `app/ai/memory/service` — create, update, expire, summarize, and delete memory.
- `app/ai/memory/policies` — retention, sensitivity, and promotion rules.
- `app/ai/memory/summarization` — compaction, canonical summaries, and memory distillation.

### Interfaces
- `MemoryRepository` for persistence operations.
- `MemoryPolicyEngine` for promotion, retention, and deletion decisions.
- `MemorySummarizer` for compressing chat and event history.

### Data flow
1. New interaction arrives.
2. Ephemeral session state is updated.
3. Policy engine decides whether state becomes durable memory.
4. Durable memory is summarized, tagged, and stored.
5. Expiry jobs remove or archive memory based on retention rules.

### Async boundaries
- Summarization, dedupe, and expiry enforcement run asynchronously for large sessions.
- Writes should be lightweight and append-only where possible.

### Caching strategy
- Cache recent session memory and summary artifacts with short TTLs.
- Cache negative lookups for nonexistent or expired memory entries.

### Scaling considerations
- Partition memory by tenant and memory class.
- Large tenants may require separate summary and retrieval queues.

### Security implications
- Memory entries must be tenant-scoped and access-controlled.
- Sensitive data should not be mirrored into logs or metrics.

## 2. Folder structure

- `app/ai/memory/entities`
- `app/ai/memory/repositories`
- `app/ai/memory/services`
- `app/ai/memory/policies`
- `app/ai/memory/summarization`
- `app/ai/memory/workers`

## 3. Service boundaries

- Session memory service: handles per-request scratch state and active conversation windows.
- Durable memory service: stores preferences, summaries, and structured memory artifacts.
- Compliance service: ensures retention, redaction, and deletion rules are honored.

## 4. Repository patterns

- Separate repositories by memory tier, not by transport.
- Repositories should expose tenant-scoped read/write APIs and batch expiration operations.
- Include content hashes, source ids, and policy tags in repository contracts.

## 5. Memory lifecycle design

- **Ephemeral**: request frame, runtime scratchpad, tool outputs.
- **Session**: active conversation turns and working summaries.
- **Durable**: tenant policy, user preferences, approved summaries, clinical context.
- **Expired**: logically deleted, archived, or permanently purged according to policy.

## 6. AI orchestration flow

- Memory is consulted before retrieval so active context can shape the query.
- Memory updates are emitted after response generation to avoid contaminating the current turn.

## 7. Retrieval architecture

- Memory retrieval should support hybrid lookup by semantic similarity, timestamp, source type, and sensitivity level.
- Session memory should be favored over durable memory for immediate context.

## 8. Async processing architecture

- Summarization, archival, and purge jobs run on background workers.
- Reprocessing must be idempotent to avoid duplicated summaries.

## 9. Vector database strategy

- Embed only approved memory classes.
- Store tenant id, memory class, sensitivity, source type, and version in metadata.
- Delete vector rows in sync with source memory deletion.

## 10. Context assembly pipeline

- Assemble memory in ordered layers: policy, session, user, tenant, and task evidence.
- Compress older turns into summaries before including them in the prompt.

## 11. Token budgeting strategy

- Session memory gets priority over durable memory when token space is constrained.
- High-confidence, compact summaries are preferred over raw verbose histories.

## 12. Prompt injection architecture

- Memory may contain adversarial content and must never be injected unfiltered.
- All memory content must pass policy and trust filters before prompt inclusion.

## 13. Tenant isolation strategy

- Memory namespaces are tenant-scoped by default.
- Cross-tenant reads require explicit administrative policy and should be rare.

## 14. Healthcare compliance considerations

- Respect retention, purge, and legal hold policies.
- Maintain deletion lineage where required by audit policy.

## 15. Scalability planning

- Scale memory writes independently from retrieval reads.
- Heavy tenants should be isolated with queue and index partitions.

## 16. Failure handling strategy

- If memory store is unavailable, continue with reduced context and issue a recoverable warning.
- If summarization fails, preserve raw session history rather than losing state.

## 17. Event-driven architecture flow

- Emit events for memory created, memory promoted, memory expired, and memory purged.
- Use events to trigger reindexing and observability counters.

## 18. Background worker architecture

- Workers run summary generation, dedupe, archival, and deletion jobs.
- Worker retries must be safe to replay.

## 19. Embedding pipeline architecture

- Memory embedding is optional by sensitivity class and policy.
- Only approved memory classes should be embedded for retrieval.

## 20. AI observability architecture

- Track memory write volume, summary throughput, expiry volume, and retrieval hit rate.
- Include memory class and tenant id in traces, never raw PHI.
