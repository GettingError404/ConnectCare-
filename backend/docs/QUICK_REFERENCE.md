# Quick Reference Guide - Stateful Conversation AI

## Quick Links

### Core Documentation
- **Architecture Overview:** [STATEFUL_CONVERSATION_ARCHITECTURE.md](./STATEFUL_CONVERSATION_ARCHITECTURE.md)
- **WebSocket Protocol:** [WEBSOCKET_PROTOCOL_V2.md](./WEBSOCKET_PROTOCOL_V2.md)
- **Implementation Guide:** [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)
- **Project Summary:** [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)

### Code Files
- **Database Migration:** `backend/alembic/versions/0014_add_stateful_conversation.py`
- **Models:** `backend/app/models/conversation.py`
- **Services:** `backend/app/services/{conversation_context,reconnect,vector_search,prompt_orchestrator}.py`
- **WebSocket Gateway:** `backend/app/websocket/gateway_v2.py`

---

## Key Concepts

### 1. Conversation Thread
A single conversation grouped at the session level. Supports multiple conversations per session.

```
Session 1
├─ Conversation 1 (topic: blood pressure)
│  ├─ Message 1 (user): "Why is my BP high?"
│  ├─ Message 2 (assistant): "Several factors..."
│  └─ Message 3 (user): "What should I do?"
└─ Conversation 2 (topic: medication)
   ├─ Message 1 (user): "Can I take this?"
   └─ Message 2 (assistant): "You should ask..."
```

### 2. Message Acknowledgment
Client must acknowledge receipt of chunks. Enables replay on disconnect.

```
User sends: user_message → Server: message_received → Streams chunks
Client receives: message_chunk → Records locally → Sends message_ack
Server receives: message_ack → Records watermark → Ready for replay
```

### 3. Token Budget
Prompt context is built within token limits. Older messages dropped if needed.

```
Total: 2000 tokens
├─ System Prompt: 100 (fixed)
├─ Current Message: 50 (fixed)
├─ Available for History: 1250
│  ├─ Recent 5 messages: 1000
│  ├─ Semantic Memories: 200
│  └─ Summarized History: fallback
└─ Reserved for Response: 500
```

### 4. Semantic Search
Uses pgvector to find relevant past context via embeddings.

```
Current Message: "My feet hurt"
    ↓ (Generate embedding)
Search pgvector: Cosine similarity > 0.7
    ↓ (Retrieve similar)
Find: [
  "I had foot pain last week, doctor said...",
  "Recommended arthritis tests...",
  "Took ibuprofen and it helped"
]
    ↓ (Include in prompt)
Better context for current response
```

### 5. Reconnect Replay
Streams all unsent messages on reconnect. Deterministic - same chunks, no regeneration.

```
Disconnect at seq 42 (message not complete)
    ↓ (Network break)
Reconnect with: last_sequence_no=42
    ↓ (Server lookup)
Find: Messages 43, 44, 45, ... pending
    ↓ (Stream from DB)
Client receives: [chunk, chunk, complete, chunk, chunk, complete, ...]
    ↓ (Replay UI)
Message seq 43 appears, then seq 44, etc.
```

---

## Service Quick Reference

### ConversationContextService
```python
# Get recent messages
recent = await context_service.get_recent_messages(
    tenant_id=tid, 
    conversation_id=cid, 
    limit=5
)

# Search semantic memories
memories = await context_service.search_semantic_memory(
    tenant_id=tid,
    conversation_id=cid,
    embedding=query_embedding,
    limit=3,
    similarity_threshold=0.7
)

# Build optimized context
context = await context_service.build_optimized_context(
    tenant_id=tid,
    conversation_id=cid,
    current_message="What about...?",
    token_budget=2000,
    system_prompt="You are...",
    user_context={"name": "John", "age": 65}
)
```

### ReconnectService
```python
# Create reconnect session
session = await reconnect_service.create_or_get_reconnect_session(
    tenant_id=tid,
    session_id=sid,
    conversation_id=cid
)

# Record acknowledgment
ack = await reconnect_service.record_message_acknowledgment(
    tenant_id=tid,
    conversation_id=cid,
    user_id=uid,
    session_id=sid,
    message_sequence_no=42,
    last_chunk_sequence_no=5
)

# Get replay events
replay = await reconnect_service.get_pending_replay(
    tenant_id=tid,
    session_id=sid,
    conversation_id=cid,
    from_sequence_no=41
)

# Generate resume token
token = await reconnect_service.generate_resume_token(
    tenant_id=tid,
    session_id=sid,
    conversation_id=cid,
    last_acked_message_no=42
)
```

### VectorSearchService
```python
# Generate embedding
embedding = await vector_service.embed_text("My back hurts")

# Search similar
results = await vector_service.search_similar(
    tenant_id=tid,
    query="back pain",
    conversation_id=cid,
    limit=5,
    similarity_threshold=0.7
)

# Reindex conversation
reindexed = await vector_service.reindex_conversation(
    tenant_id=tid,
    conversation_id=cid
)
```

### PromptOrchestratorService
```python
# Build minimal prompt (fast path)
prompt = await orchestrator.build_minimal_prompt(
    tenant_id=tid,
    conversation_id=cid,
    user_message="What should I do?"
)

# Build full prompt (comprehensive)
prompt = await orchestrator.build_full_context_prompt(
    tenant_id=tid,
    conversation_id=cid,
    user_message="What should I do?",
    user_profile={"name": "John", "age": 65}
)

# Result structure
{
  "system_prompt": "You are an empathetic...",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "system", "content": "[Memory] ..."},
  ],
  "metadata": {
    "total_tokens": 1850,
    "truncated": false,
    "context_sources": ["recent_messages", "semantic_memories"]
  }
}
```

---

## WebSocket Message Cheat Sheet

### Client → Server

**Send Message**
```json
{
  "type": "user_message",
  "message_id": "uuid",
  "conversation_id": "uuid",
  "content": "What should I do?",
  "language": "en"
}
```

**Acknowledge**
```json
{
  "type": "message_ack",
  "message_id": "uuid",
  "conversation_id": "uuid",
  "sequence_no": 42,
  "last_chunk_no": 5
}
```

**Reconnect**
```json
{
  "type": "reconnect",
  "conversation_id": "uuid",
  "last_sequence_no": 42,
  "resume_token": "jwt-token"
}
```

**Heartbeat**
```json
{
  "type": "heartbeat_ack"
}
```

### Server → Client

**Stream Chunk**
```json
{
  "type": "message_chunk",
  "message_id": "uuid",
  "sequence_no": 43,
  "chunk_index": 0,
  "content": "You should...",
  "delta_tokens": 15
}
```

**Stream Complete**
```json
{
  "type": "message_complete",
  "message_id": "uuid",
  "sequence_no": 43,
  "total_chunks": 12,
  "total_tokens": 215
}
```

**Replay**
```json
{
  "type": "replay_start",
  "conversation_id": "uuid",
  "pending_messages": 2
}
```

**Error**
```json
{
  "type": "error",
  "error_code": "internal_error",
  "message": "Failed to process..."
}
```

---

## Common Scenarios

### Scenario 1: User Sends Message → Gets Streamed Response

```
1. Client sends: user_message
2. Server responds: message_received
3. Server streams: message_chunk (multiple)
4. Server sends: message_complete
5. Client sends: message_ack
6. Server records: Watermark updated
```

### Scenario 2: Network Fails Mid-Stream

```
1. Network breaks (chunk 3 of 10 received)
2. Client reconnects with: reconnect (last_sequence_no=X)
3. Server looks up: Chunks after sequence X
4. Server sends: replay_start + all chunks from chunk 0
5. Client replays: Updates UI with all chunks
6. Client sends: message_ack when complete
```

### Scenario 3: User Asks Follow-up Question

```
1. Conversation already exists (has history)
2. Client sends: user_message (same conversation_id)
3. Server calls: context_service.get_recent_messages()
4. Server calls: vector_service.search_similar()
5. Server builds: Full prompt with context
6. Server sends to agent: Full prompt including history
7. Agent responds with contextual answer
8. Stream continues as normal
```

### Scenario 4: Reconnect After 1 Hour

```
1. Reconnect message has resume_token from earlier
2. Server validates: Token not expired (30 min TTL)
3. Resume token invalid (expired)
4. Client must provide: last_sequence_no fallback
5. Server retrieves: All unsent messages since that sequence
6. Replay continues as normal
```

---

## Database Queries

### Find Unacked Messages
```sql
SELECT m.* FROM ai_messages m
LEFT JOIN message_acknowledgments a 
  ON a.message_sequence_no = m.sequence_no
WHERE m.conversation_id = $conversation_id
  AND a.id IS NULL  -- Not acknowledged
ORDER BY m.sequence_no;
```

### Get Conversation History
```sql
SELECT * FROM ai_messages
WHERE conversation_id = $id
  AND deleted_at IS NULL
ORDER BY sequence_no DESC
LIMIT 10;
```

### Search Semantic Memories
```sql
SELECT m.*, 
  1 - (e.embedding <=> $query_embedding) as similarity
FROM ai_memory_summaries m
JOIN ai_memory_embeddings e ON e.memory_summary_id = m.id
WHERE m.conversation_id = $id
ORDER BY similarity DESC
LIMIT 5;
```

### Count Pending Messages
```sql
SELECT COUNT(DISTINCT sequence_no)
FROM streaming_chunks sc
LEFT JOIN message_acknowledgments ma 
  ON ma.message_sequence_no >= sc.sequence_no
WHERE sc.session_id = $session_id
  AND ma.id IS NULL;
```

---

## Performance Tips

### Speed Up Context Building
1. Index on `ai_messages(conversation_id, sequence_no DESC)` ✓
2. Pre-compute embeddings async (Celery) ✓
3. Cache recent messages (Redis) - Consider
4. Batch semantic searches - Use multi-embedding APIs

### Reduce Token Usage
1. Summarize old messages (after 1 week) - Implement
2. Use cosine similarity threshold 0.8+ (stricter) - Tune
3. Reserve less space for response (20% instead of 25%) - Experiment
4. Reduce recent message count (3 instead of 5) - A/B test

### Improve Reconnect Speed
1. Keep streaming chunks in hot storage - Done
2. Use sequential chunk_index lookup - Done
3. Cache reconnect sessions (5 min) - Consider
4. Pre-warm replay query - Measure

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `missing_token` | JWT not in query params | Check WebSocket URL includes `?token=` |
| `invalid_token` | Token expired or forged | Refresh token, re-authenticate |
| `missing_conversation_id` on reconnect | Client didn't send conversation_id | Require conversation_id in reconnect msg |
| `invalid_resume_token` | Token expired (30 min max) | Use last_sequence_no as fallback |
| `empty_message` | Content is empty string | Validate client-side before send |
| `context_truncated` | Too many messages in context | Increase token_budget or summarize |
| `embedding_generation_failed` | OpenAI API error | Check OPENAI_API_KEY, retry with backoff |

---

## Monitoring Checklist

### Per-Hour Metrics
- [ ] Active WebSocket connections
- [ ] Messages processed
- [ ] Avg first-chunk latency
- [ ] Error rate

### Per-Day Metrics
- [ ] Conversation count
- [ ] Avg messages per conversation
- [ ] Context truncation rate
- [ ] Reconnect frequency
- [ ] Successful replay rate

### Per-Week Metrics
- [ ] Token usage trend
- [ ] Embedding generation latency
- [ ] Vector search performance
- [ ] Database query times
- [ ] Reconnect success rate

---

## Useful Commands

```bash
# Run database migration
cd backend
alembic upgrade head

# Test models import
python -c "from app.models.conversation import ConversationThread; print('OK')"

# Generate embedding
python -c "
from app.services.vector_search import VectorSearchService
import asyncio

async def test():
    svc = VectorSearchService(None)
    emb = await svc.embed_text('hello world')
    print(f'Dimension: {len(emb)}')

asyncio.run(test())
"

# Query recent messages
python -c "
from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT id, role, content 
        FROM ai_messages 
        ORDER BY created_at DESC LIMIT 5
    '''))
    for row in result:
        print(row)
"

# Check table sizes
python -c "
from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    tables = ['conversation_threads', 'ai_messages', 'streaming_chunks']
    for table in tables:
        result = conn.execute(text(f'SELECT COUNT(*) FROM {table}'))
        print(f'{table}: {result.scalar()}')
"
```

---

## Next Steps Checklist

**This Week:**
- [ ] Review all documentation
- [ ] Run migration in staging
- [ ] Test model imports
- [ ] Deploy services code

**Next Week:**
- [ ] Deploy gateway_v2
- [ ] Begin frontend integration
- [ ] Load test (100+ concurrent)
- [ ] Security audit

**Week 3:**
- [ ] Production rollout (10% traffic)
- [ ] Monitor metrics
- [ ] Gather feedback
- [ ] Full rollout (100%)

---

**Version:** 1.0  
**Updated:** 2026-05-26  
**Maintainer:** Backend Team
