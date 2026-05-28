# Stateful Conversational AI System Architecture

**Version:** 1.0  
**Date:** 2026-05-26  
**Status:** Architecture Design  

## Executive Summary

Transforms the current stateless WebSocket streaming system into a stateful conversational AI platform with:
- Persistent conversation memory
- Contextual retrieval using embeddings
- Stream recovery and reconnect replay
- Token-aware context windows
- Production-grade reliability

---

## Current System (Stateless)

```
Frontend
   ↓ WS
[WS Gateway] ← JWT + Session validation
   ↓ (Redis Event Bus)
[Agent Connector] → [AI Agent Stream] → Response chunks
   ↓
Frontend (no memory, no replay)
```

**Limitations:**
- No persistent conversation history
- No reconnect recovery
- No contextual continuity between sessions
- No long-term memory or semantic retrieval
- Interrupted streams lost forever

---

## Target System (Stateful)

```
Frontend (React/Vue)
   ↓ WS with conversation_id
[WS Gateway]
   ├─ JWT + Session validation
   ├─ Conversation context loading
   └─ Message acknowledgment tracking
   ↓ (Redis Event Bus)
[Conversation Context Service]
   ├─ Retrieve recent history (PostgreSQL)
   ├─ Semantic memory search (pgvector)
   ├─ Build optimized prompt context
   └─ Token-aware truncation
   ↓
[Prompt Orchestrator]
   ├─ System prompt
   ├─ User profile context
   ├─ Recent messages (recent_N window)
   ├─ Retrieved semantic memories
   ├─ Summarized long-term context
   └─ Current user message
   ↓
[AI Agent Stream]
   ├─ Process optimized prompt
   └─ Stream response chunks
   ↓
[Event Bus - Persistence Layer]
   ├─ Save streaming chunks → StreamingChunk table
   ├─ Generate embeddings → async Celery
   ├─ Publish memory_indexed event
   ├─ Track message acknowledgment
   └─ Store final message → AIMessage
   ↓
Frontend (with replay capability)
```

---

## Core Concepts

### 1. Conversation Model

A conversation is a thread of alternating user and assistant messages within a session.

```
Conversation (new model)
├─ id (UUID)
├─ tenant_id (FK)
├─ user_id (FK)
├─ session_id (FK) → UserSession
├─ conversation_id (unique per session)
├─ title (auto-generated or user-set)
├─ status (active, archived, deleted)
├─ created_at, updated_at
└─ metadata (context, mode, language)
    Message (enhanced AIMessage)
    ├─ id
    ├─ conversation_id (FK)
    ├─ role (user, assistant)
    ├─ content (full text or initial chunk)
    ├─ sequence_no (ordering within conversation)
    ├─ is_streaming (false when complete)
    ├─ token_count (for context window calc)
    ├─ recorded_at (event-time)
    ├─ acknowledged_by_client (bool)
    └─ metadata
        StreamingChunk
        ├─ id
        ├─ message_id
        ├─ chunk_index (0, 1, 2...)
        ├─ content (delta)
        ├─ sequence_no (global sequence across session)
        └─ persisted_at
```

### 2. Context Windows

**Recent Context Window (short-term memory)**
- Last N messages (configurable, e.g., 5-10)
- Always included in prompt
- Fast retrieval from PostgreSQL
- Full message content

**Long-term Memory (summarized)**
- Older messages summarized into atomic units
- Stored as AIMemorySummary
- Indexed with embeddings
- Included conditionally based on relevance

**Semantic Memory (vector-retrieved)**
- Retrieved via pgvector similarity search
- Based on semantic relevance to current query
- Top-K results merged with prompt context
- Reduces token waste on irrelevant history

### 3. Token-Aware Context Truncation

Algorithm:
1. Start with system prompt (fixed token budget)
2. Add user profile/context (fixed)
3. Add current user message (variable)
4. Calculate remaining budget: `total_budget - used_tokens`
5. Add recent messages (oldest first, backward): until budget exhausted
6. Fallback to summarized memories if needed
7. Emit `context_truncated` event if dropped messages

### 4. Message Acknowledgment & Reliability

**Stream Completion Flow:**
```
User sends message
    ↓ (immediate)
Server assigns message_id + message_sequence_no
    ↓ (streaming)
Each chunk sent with chunk_sequence_no
    ↓ (client receives chunks)
Client sends ack with message_id + last_chunk_no
    ↓ (server receives ack)
Server records acknowledged position → ReconnectSession.last_acked_message_no
    ↓ (stream finishes)
Server sends stream_complete event
    ↓ (client receives final ack)
If disconnect: on reconnect, replay unacked chunks
```

### 5. Reconnect & Replay Protocol

**Reconnect Request:**
```json
{
  "type": "reconnect",
  "conversation_id": "uuid",
  "last_sequence_no": 42,  // last seen message sequence
  "resume_token": "encoded-jwt-with-state"
}
```

**Replay Response:**
```json
{
  "type": "replay_start",
  "conversation_id": "uuid",
  "replay_messages": [
    {"type": "message_chunk", "sequence_no": 43, "content": "chunk..."},
    {"type": "message_complete", "sequence_no": 43},
    ...
  ],
  "replay_end_sequence_no": 45
}
```

---

## Database Schema Enhancements

### New Tables

```sql
-- Thread/Conversation grouping
CREATE TABLE conversation_threads (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id UUID NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    title VARCHAR(255),
    description TEXT,
    status VARCHAR(32) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    FOREIGN KEY (tenant_id, user_id) REFERENCES users(tenant_id, id)
);

-- Message acknowledgment tracking
CREATE TABLE message_acknowledgments (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversation_threads(id),
    user_id UUID NOT NULL REFERENCES users(id),
    session_id UUID NOT NULL REFERENCES user_sessions(id),
    message_sequence_no INT NOT NULL,
    last_chunk_sequence_no INT NOT NULL,
    acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(session_id, message_sequence_no)
);

-- Streaming chunks for incremental message delivery
CREATE TABLE streaming_chunks (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    message_id UUID NOT NULL REFERENCES ai_messages(id),
    sequence_no INT NOT NULL,  -- global per-session sequence
    chunk_index INT NOT NULL,  -- 0, 1, 2... within message
    content TEXT NOT NULL,
    delta_tokens INT,
    persisted_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_streaming_by_message (message_id, chunk_index)
);

-- Reconnect session state
CREATE TABLE reconnect_sessions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    session_id UUID NOT NULL REFERENCES user_sessions(id),
    conversation_id UUID NOT NULL REFERENCES conversation_threads(id),
    last_acked_message_sequence_no INT NOT NULL DEFAULT 0,
    last_acked_chunk_sequence_no INT NOT NULL DEFAULT 0,
    pending_replay_count INT DEFAULT 0,
    resume_token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, conversation_id)
);

-- Context window metadata
CREATE TABLE context_windows (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    conversation_id UUID NOT NULL REFERENCES conversation_threads(id),
    recent_message_count INT NOT NULL DEFAULT 5,
    total_tokens_in_window INT NOT NULL,
    truncated BOOLEAN DEFAULT FALSE,
    truncation_reason VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_context_by_conversation (conversation_id)
);
```

### Enhanced ai_messages Table

```sql
ALTER TABLE ai_messages ADD COLUMN (
    conversation_id UUID REFERENCES conversation_threads(id),
    sequence_no INT NOT NULL,  -- ordering within conversation
    parent_message_id UUID REFERENCES ai_messages(id),  -- for threading
    is_streaming BOOLEAN DEFAULT FALSE,
    stream_complete BOOLEAN DEFAULT FALSE,
    acknowledged_by_client BOOLEAN DEFAULT FALSE,
    INDEX idx_ai_messages_sequence (conversation_id, sequence_no),
    INDEX idx_ai_messages_streaming (is_streaming, stream_complete)
);
```

### Indexes for Performance

```sql
-- Recent message retrieval
CREATE INDEX idx_ai_messages_recent 
ON ai_messages(conversation_id, sequence_no DESC)
WHERE deleted_at IS NULL;

-- Vector search
CREATE INDEX idx_ai_memory_embedding 
ON ai_memory_embeddings 
USING ivfflat (embedding vector_cosine_ops);

-- Session-based queries
CREATE INDEX idx_reconnect_active 
ON reconnect_sessions(session_id, conversation_id)
WHERE resume_token_expires_at > NOW();
```

---

## Service Architecture

### 1. ConversationContextService

**Purpose:** Retrieves and optimizes context for prompt building

**Methods:**
```python
async def get_recent_messages(
    tenant_id: UUID,
    conversation_id: UUID,
    limit: int = 5
) -> list[AIMessage]:
    """Fetch last N messages from conversation."""

async def search_semantic_memory(
    tenant_id: UUID,
    conversation_id: UUID,
    query: str,
    limit: int = 3,
    similarity_threshold: float = 0.7
) -> list[AIMemorySummary]:
    """Vector search for relevant historical context."""

async def get_summarized_history(
    tenant_id: UUID,
    conversation_id: UUID,
    exclude_recent_minutes: int = 60
) -> list[AIMemorySummary]:
    """Retrieve summarized long-term memories."""

async def build_optimized_context(
    tenant_id: UUID,
    conversation_id: UUID,
    current_message: str,
    token_budget: int = 2000
) -> dict:
    """Build prompt context respecting token limits."""
    # Returns: {
    #   "system_prompt": "...",
    #   "user_context": {...},
    #   "recent_messages": [...],
    #   "semantic_memories": [...],
    #   "context_metadata": {
    #     "total_tokens": 1850,
    #     "truncated": false
    #   }
    # }
```

### 2. MemoryPipelineService

**Purpose:** Async processing of conversation data into memory

**Workflow:**
```
User message saved to AIMessage
    ↓ event: message_saved
    
Process message:
    - Generate embeddings (via Celery)
    - Create memory chunks
    - Index for semantic search
    
Periodically (configurable):
    - Summarize old messages
    - Compress long contexts
    - Expire old memories
    - Reindex embeddings
```

**Methods:**
```python
async def on_message_persisted(message: AIMessage):
    """Trigger embedding generation and chunking."""

async def index_message_for_search(message: AIMessage):
    """Create searchable embedding."""

async def summarize_conversation_window(
    conversation_id: UUID,
    start_sequence: int,
    end_sequence: int
):
    """Summarize messages into memory units."""

async def cleanup_old_memories(
    tenant_id: UUID,
    older_than_days: int = 30
):
    """Archive/compress old conversation data."""
```

### 3. ReconnectService

**Purpose:** Manage session resumption and stream replay

**Methods:**
```python
async def create_reconnect_session(
    tenant_id: UUID,
    session_id: UUID,
    conversation_id: UUID
) -> dict:
    """Initialize reconnect state."""

async def get_pending_replay(
    session_id: UUID,
    conversation_id: UUID,
    from_sequence_no: int
) -> list[dict]:
    """Retrieve unacked messages for replay."""

async def ack_message(
    session_id: UUID,
    conversation_id: UUID,
    message_sequence_no: int,
    last_chunk_no: int
):
    """Record client acknowledgment."""

async def validate_resume_token(
    session_id: UUID,
    resume_token: str
) -> bool:
    """Verify resume token validity."""
```

### 4. PromptOrchestratorService

**Purpose:** Build final optimized prompt for AI agent

**Methods:**
```python
async def orchestrate_prompt(
    tenant_id: UUID,
    conversation_id: UUID,
    user_message: str,
    user_profile: dict,
    config: dict
) -> dict:
    """Build complete prompt context."""
    # Returns: {
    #   "system_prompt": "...",
    #   "messages": [
    #     {"role": "user", "content": "..."},
    #     {"role": "assistant", "content": "..."},
    #     ...
    #   ],
    #   "metadata": {
    #     "context_source": ["recent", "semantic", "summarized"],
    #     "token_count": 1850,
    #     "truncation_reason": null
    #   }
    # }
```

### 5. VectorSearchService

**Purpose:** Semantic memory retrieval via pgvector

**Methods:**
```python
async def embed_text(text: str) -> list[float]:
    """Generate embedding for text."""

async def search_similar(
    tenant_id: UUID,
    embedding: list[float],
    limit: int = 5,
    threshold: float = 0.7
) -> list[AIMemorySummary]:
    """Find similar memories via vector search."""

async def reindex_conversation(
    conversation_id: UUID
):
    """Regenerate embeddings for conversation."""
```

---

## WebSocket Protocol

### Message Types

**User Message:**
```json
{
  "type": "user_message",
  "message_id": "uuid",
  "conversation_id": "uuid",
  "content": "What should I do about my high blood pressure?",
  "language": "en",
  "metadata": {"voice": true, "source": "mobile"}
}
```

**Stream Chunk (Server → Client):**
```json
{
  "type": "message_chunk",
  "message_id": "uuid",
  "sequence_no": 42,
  "chunk_index": 0,
  "content": "You should consider...",
  "delta_tokens": 15
}
```

**Message Complete:**
```json
{
  "type": "message_complete",
  "message_id": "uuid",
  "sequence_no": 42,
  "total_tokens": 215,
  "acknowledged": false
}
```

**Client Acknowledgment:**
```json
{
  "type": "message_ack",
  "message_id": "uuid",
  "sequence_no": 42,
  "last_chunk_no": 5
}
```

**Reconnect:**
```json
{
  "type": "reconnect",
  "conversation_id": "uuid",
  "last_sequence_no": 42,
  "resume_token": "eyJ..."
}
```

**Replay Start (Server Response):**
```json
{
  "type": "replay_start",
  "conversation_id": "uuid",
  "replay_messages": [
    {"type": "message_chunk", "sequence_no": 43, "chunk_index": 0, "content": "..."},
    {"type": "message_complete", "sequence_no": 43}
  ],
  "replay_complete_sequence_no": 45
}
```

---

## Event Bus Design

### Event Types

| Event | Source | Handler | Persistence |
|-------|--------|---------|-------------|
| `message_created` | WS Gateway | ConversationService, MemoryPipeline | PostgreSQL |
| `message_chunk_received` | Agent Connector | EventBus publisher | StreamingChunk table |
| `message_complete` | Agent Connector | EventBus, ReconnectService | AIMessage update |
| `message_acked` | WS Gateway | ReconnectService | message_acknowledgments |
| `embedding_generated` | Celery task | VectorSearchService | ai_memory_embeddings |
| `memory_summarized` | Celery task | MemoryPipelineService | ai_memory_summaries |
| `reconnect_initiated` | WS Gateway | ReconnectService | reconnect_sessions |
| `replay_complete` | WS Gateway | ReconnectService | session state update |

### Redis Pub/Sub Channels

```
conversation:{tenant_id}:{session_id}:messages     # Message events
conversation:{tenant_id}:{session_id}:replay       # Replay events
memory:{tenant_id}:embeddings                       # Embedding updates
memory:{tenant_id}:summarization                    # Summarization updates
alerts:{tenant_id}                                  # Alert broadcasts
```

---

## Scalability Considerations

### Horizontal Scaling

**Per-process state:**
- WebSocket connections in ConnectionManager (in-memory)
- Redis for cross-process coordination
- PostgreSQL for persistent state

**Multiple worker instances:**
```
Load Balancer
├─ Worker 1 (WebSocket connections, streaming)
├─ Worker 2 (WebSocket connections, streaming)
└─ Worker N ...

Shared state:
├─ PostgreSQL (persistent)
├─ Redis (event bus, session state)
└─ pgvector (embeddings)
```

### Async Task Distribution

```
Celery workers (separate process pool):
├─ embedding_queue: Generate embeddings (GPU optional)
├─ summarization_queue: Summarize messages
├─ indexing_queue: Update vector indexes
├─ cleanup_queue: Archive old data
└─ priority: Critical operations first
```

---

## Security Model

### Conversation Ownership

Every operation validates:
```python
# Pseudo-code
def verify_conversation_access(
    user_id: UUID,
    tenant_id: UUID,
    conversation_id: UUID
):
    conversation = db.get(Conversation, conversation_id)
    
    # Multi-level validation
    assert conversation.tenant_id == tenant_id  # Tenant isolation
    assert conversation.user_id == user_id       # User ownership
    assert conversation.deleted_at is None       # Not soft-deleted
    
    return conversation
```

### Secure Session Restoration

- Resume tokens are short-lived JWTs
- Include session_id + conversation_id in token
- Verify JWT signature and expiry
- Rate-limit reconnect attempts

### Encryption at Rest

- Embeddings encrypted in pgvector columns
- Message content encrypted if PII present
- Audit trail for access and modifications

---

## Production Deployment Checklist

- [ ] Database migrations applied
- [ ] pgvector extension installed
- [ ] Celery workers running (separate pods)
- [ ] Redis pub/sub tested under load
- [ ] Monitoring configured (metrics, logs, traces)
- [ ] Rate limiting on reconnect endpoints
- [ ] Message queue prioritization configured
- [ ] Backup strategy for conversation data
- [ ] Vector index maintenance scheduled
- [ ] Client-side reconnect logic tested
- [ ] Load testing (concurrent connections, replays)

---

## Migration Path

### Phase 1: Database & Models (Week 1)
- Create new tables
- Add indexes
- Run migrations
- Deploy with backward compatibility

### Phase 2: Services Layer (Week 1-2)
- Implement ConversationContextService
- Implement MemoryPipelineService
- Implement VectorSearchService
- Add async Celery tasks

### Phase 3: WebSocket Enhancement (Week 2)
- Add conversation_id tracking
- Implement message acknowledgment
- Add reconnect protocol
- Update frontend WebSocket client

### Phase 4: Production Hardening (Week 3)
- Load testing
- Error recovery scenarios
- Monitoring setup
- Performance tuning

---

## References

- pgvector documentation: https://github.com/pgvector/pgvector
- FastAPI WebSocket guide: https://fastapi.tiangolo.com/advanced/websockets/
- Redis Streams vs Pub/Sub: https://redis.io/docs/latest/develop/interact/pubsub/
- Token counting: tiktoken library
