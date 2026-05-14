# Retrieval Pipeline — ConnectedCare+

STATUS: PLANNED (NOT IMPLEMENTED)
Last verified against repository state: 2026-05-09

Purpose

This document defines how AI context is discovered, filtered, ranked, and assembled into a bounded prompt for the model.

## 1. Retrieval architecture

### Responsibilities
- Transform user intent and task metadata into a high-quality, tenant-safe context set.
- Combine memory, vector search, structured lookups, and policy constraints.

### Modules
- `app/ai/retrieval/intent` — query framing and retrieval intent classification.
- `app/ai/retrieval/filtering` — tenant, sensitivity, and policy filters.
- `app/ai/retrieval/ranking` — relevance scoring and reranking.
- `app/ai/retrieval/assembly` — prompt-ready context selection.

### Interfaces
- `RetrievalService.retrieve(req

uest)` returns ranked candidates.
- `ContextAssembler.build(candidates)` returns prompt-safe context.

### Data flow
1. Intent classification determines retrieval scope.
2. Filters remove disallowed or irrelevant records.
3. Ranker scores and orders candidates.
4. Assembler compresses and packages the final context.

### Async boundaries
- Retrieval should be synchronous and low-latency; precomputation can happen asynchronously.

### Caching strategy
- Cache hot queries and rerank results briefly.
- Cache structured policy constraints separately from content.

### Scaling considerations
- Keep read latency predictable by limiting candidate fan-out.
- Separate heavy indexing from read traffic.

### Security implications
- This is future-facing only.
