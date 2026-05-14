# Context Engineering — ConnectedCare+

STATUS: PLANNED (NOT IMPLEMENTED)
Last verified against repository state: 2026-05-09

Purpose

This document defines how prompts are assembled, budgeted, sanitized, and protected against injection in the ConnectedCare+ AI platform.

## 1. Context assembly pipeline

### Responsibilities
- Construct a safe, compact, well-ordered prompt context for each AI request.
- Balance memory, retrieval, system policy, and response constraints.

### Modules
- `app/ai/context/system` — system policy and behavioral constraints.
- `app/ai/context/memory` — session and durable memory selection.
- `app/ai/context/retrieval` — ranked evidence inclusion.
- `app/ai/context/tools` — tool output normalization.
- `app/ai/context/budget` — token accounting and truncation.

### Interfaces
- `ContextBuilder.build(request, sources)` returns a prompt bundle.
- `TokenBudgeter.allocate(bundle)` returns source budgets and truncation decisions.

### Data flow
1. Build policy frame.
2. Select memory and retrieval sources.
3. Normalize and sanitize each source.
4. Budget tokens and truncate/summarize as needed.
5. Emit final context with provenance.

### Async boundaries
- Pre-summarization and source normalization can happen in workers.

### Caching strategy
- Cache prompt templates, policy frames, and stable tool schemas.

### Scaling considerations
- Context assembly must remain linear with bounded source counts.

### Security implications
- This is future-facing only.
