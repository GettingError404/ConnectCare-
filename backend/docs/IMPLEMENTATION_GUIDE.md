# Implementation Guide: Stateful Conversation AI

**Target Audience:** Backend engineers, DevOps  
**Timeline:** 3 weeks  
**Complexity:** Advanced  

---

## Prerequisites

- Python 3.10+
- PostgreSQL 14+ with pgvector extension
- Redis 6.0+
- FastAPI application running
- Existing AI agent service

---

## Phase 1: Database & Schema (Days 1-2)

### 1.1 Apply Migration

```bash
cd backend
alembic upgrade head
```

This creates:
- `conversation_threads` table
- `message_acknowledgments` table
- `streaming_chunks` table
- `reconnect_sessions` table
- `context_windows` table
- Indexes for performance

### 1.2 Verify Tables

```sql
-- Verify tables created
\dt conversation_threads
\dt streaming_chunks
\dt reconnect_sessions

-- Check pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify existing pgvector tables
\dt ai_memory_embeddings
```

### 1.3 Test Connection

```bash
python -c "
from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM conversation_threads'))
    print(f'conversation_threads: {result.scalar()} rows')
"
```

---

## Phase 2: Models & Services (Days 2-4)

### 2.1 Verify Model Imports

```bash
cd backend
python -c "
from app.models.conversation import ConversationThread, StreamingChunk, ReconnectSession
from app.models.ai_memory import AIMessage
print('✓ All models imported successfully')
"
```

### 2.2 Initialize Services

Create service factory in `app/services/__init__.py`:

```python
from app.services.conversation_context import ConversationContextService
from app.services.reconnect import ReconnectService
from app.services.vector_search import VectorSearchService
from app.services.prompt_orchestrator import PromptOrchestratorService

__all__ = [
    "ConversationContextService",
    "ReconnectService",
    "VectorSearchService",
    "PromptOrchestratorService",
]
```

### 2.3 Configure Services in Router

In `app/websocket/gateway_v2.py`, services are initialized per connection:

```python
@router.websocket("/ws/stream/v2")
async def ws_stream_v2(
    websocket: WebSocket,
    token: str = Query(None),
    tenant_id: str = Query(None),
):
    # ... authentication ...
    
    db_session = get_async_db()
    
    # Initialize services
    context_service = ConversationContextService(db_session)
    reconnect_service = ReconnectService(db_session)
    vector_service = VectorSearchService(db_session)
    prompt_orchestrator = PromptOrchestratorService(
        db_session=db_session,
        context_service=context_service,
        vector_service=vector_service,
    )
    
    # Services now available for entire connection lifetime
```

---

## Phase 3: WebSocket Integration (Days 4-6)

### 3.1 Mount New Endpoint

In `app/api/v1/gateway_ws_stream.py`:

```python
from fastapi import APIRouter
from app.websocket.gateway_v2 import router as stream_router_v2

router = APIRouter()

# Keep existing v1 endpoint for backward compatibility
from app.websocket.gateway import router as stream_router_v1
router.include_router(stream_router_v1)

# Add new v2 endpoint
router.include_router(stream_router_v2, prefix="/v2")
```

### 3.2 Test Endpoint

```bash
# Test WebSocket connection
python -m pytest tests/test_websocket_v2.py -v

# Or manual test:
python scripts/test_ws_client.py \
  --url ws://localhost:8000/api/v1/ws/stream/v2 \
  --token <jwt_token> \
  --tenant-id <tenant_id>
```

### 3.3 Verify in OpenAPI Docs

Navigate to: http://localhost:8000/docs

Under "WebSockets", should see both:
- `/ws/stream` (v1, existing)
- `/ws/stream/v2` (v2, new stateful)

---

## Phase 4: Vector Search Setup (Days 5-7)

### 4.1 Configure Embedding Model

In `app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing config ...
    
    # Embedding configuration
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    EMBEDDING_MODEL: str = "text-embedding-3-small"  # OpenAI
    EMBEDDING_DIMENSION: int = 1536  # text-embedding-3-small output size
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

Update `.env`:

```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
EMBEDDING_MODEL=text-embedding-3-small
```

### 4.2 Test Embedding Generation

```python
import asyncio
from app.services.vector_search import VectorSearchService
from app.db.session import AsyncSessionLocal

async def test_embeddings():
    db = AsyncSessionLocal()
    vector_service = VectorSearchService(db)
    
    # Test embedding
    text = "What should I do about high blood pressure?"
    embedding = await vector_service.embed_text(text)
    
    print(f"✓ Generated embedding: {len(embedding)} dimensions")
    assert len(embedding) == 1536
    
    await db.close()

asyncio.run(test_embeddings())
```

### 4.3 Set Up Async Embedding Tasks

In `app/tasks/embedding_tasks.py`:

```python
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(queue="embedding", bind=True, max_retries=3)
def generate_message_embedding(self, memory_summary_id: str, text: str, tenant_id: str):
    """Async task to generate and store embedding."""
    try:
        from app.services.vector_search import VectorSearchService
        from app.db.session import AsyncSessionLocal
        from uuid import UUID
        import asyncio
        
        async def _task():
            db = AsyncSessionLocal()
            vector_service = VectorSearchService(db)
            
            embedding = await vector_service.embed_text(text)
            await vector_service.store_embedding(
                tenant_id=UUID(tenant_id),
                memory_summary_id=UUID(memory_summary_id),
                embedding=embedding,
            )
            
            await db.close()
            
            logger.info(f"Embedding stored for memory: {memory_summary_id}")
        
        asyncio.run(_task())
        
    except Exception as exc:
        logger.exception(f"Embedding generation failed: {exc}")
        self.retry(exc=exc, countdown=60)  # Retry in 60 seconds
```

### 4.4 Trigger Embeddings on Message

In `app/websocket/gateway_v2.py`, after message is persisted:

```python
from app.tasks.embedding_tasks import generate_message_embedding

# After saving assistant message
generate_message_embedding.apply_async(
    args=[
        str(user_msg.id),
        content,
        str(tenant_id),
    ],
    countdown=5,  # Delay 5 seconds
    priority=8,  # Medium priority
)
```

---

## Phase 5: Context Building & Optimization (Days 6-8)

### 5.1 Test Context Service

```python
import asyncio
from uuid import UUID
from app.services.conversation_context import ConversationContextService
from app.db.session import AsyncSessionLocal

async def test_context():
    db = AsyncSessionLocal()
    context_service = ConversationContextService(db)
    
    tenant_id = UUID("...")
    conversation_id = UUID("...")
    
    # Get recent messages
    recent = await context_service.get_recent_messages(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        limit=5,
    )
    print(f"✓ Retrieved {len(recent)} recent messages")
    
    # Build context
    context = await context_service.build_optimized_context(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        current_message="What about my medications?",
        token_budget=2000,
    )
    print(f"✓ Context built: {context['context_metadata']['total_tokens']} tokens")
    
    await db.close()

asyncio.run(test_context())
```

### 5.2 Configure Token Counting

Install tiktoken:

```bash
pip install tiktoken
```

Test in prompt orchestrator:

```python
import tiktoken

encoding = tiktoken.encoding_for_model("gpt-4")
text = "Hello world"
tokens = len(encoding.encode(text))
print(f"'{text}' = {tokens} tokens")
```

### 5.3 Monitor Truncation

Log truncation events:

```python
# In ConversationContextService.build_optimized_context
if truncated:
    logger.warning(
        "context_truncated",
        extra={
            "conversation_id": str(conversation_id),
            "reason": truncation_reason,
            "available_tokens": available_for_history,
        },
    )
```

---

## Phase 6: Reconnect & Replay (Days 8-10)

### 6.1 Test Reconnect Flow

```python
import asyncio
from uuid import UUID
from app.services.reconnect import ReconnectService
from app.db.session import AsyncSessionLocal

async def test_reconnect():
    db = AsyncSessionLocal()
    reconnect_service = ReconnectService(db)
    
    tenant_id = UUID("...")
    session_id = UUID("...")
    conversation_id = UUID("...")
    
    # Create reconnect session
    session = await reconnect_service.create_or_get_reconnect_session(
        tenant_id=tenant_id,
        session_id=session_id,
        conversation_id=conversation_id,
    )
    print(f"✓ Reconnect session created: {session.id}")
    
    # Record ack
    ack = await reconnect_service.record_message_acknowledgment(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        user_id=UUID("..."),
        session_id=session_id,
        message_sequence_no=1,
        last_chunk_sequence_no=5,
    )
    print(f"✓ Ack recorded for message 1")
    
    # Generate resume token
    token = await reconnect_service.generate_resume_token(
        tenant_id=tenant_id,
        session_id=session_id,
        conversation_id=conversation_id,
        last_acked_message_no=1,
    )
    print(f"✓ Resume token generated")
    
    # Validate token
    payload = await reconnect_service.validate_resume_token(token)
    print(f"✓ Resume token valid: {payload}")
    
    # Get replay
    replay = await reconnect_service.get_pending_replay(
        tenant_id=tenant_id,
        session_id=session_id,
        conversation_id=conversation_id,
        from_sequence_no=1,
    )
    print(f"✓ Replay events: {len(replay)}")
    
    await db.close()

asyncio.run(test_reconnect())
```

### 6.2 Load Test Replay

```bash
# Generate test data
python scripts/generate_test_conversations.py \
  --conversations 100 \
  --messages-per-conversation 20 \
  --chunks-per-message 10

# Run replay test
python scripts/test_reconnect_replay.py \
  --concurrent-clients 50 \
  --replay-messages 20 \
  --duration-seconds 60
```

---

## Phase 7: Production Hardening (Days 10-14)

### 7.1 Error Handling & Timeouts

In `app/websocket/gateway_v2.py`:

```python
# Connection timeout
async def connection_monitor():
    while True:
        await asyncio.sleep(1)
        stale = await manager.cleanup_stale()
        if stale:
            logger.info(f"Cleaned {stale} stale connections")

# Message timeout
async with asyncio.timeout(30):  # 30-second timeout
    async for chunk_evt in connector.stream_text(req):
        await websocket.send_json(chunk_evt)
```

### 7.2 Rate Limiting

In `app/middleware/rate_limit.py`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Apply to WebSocket:
# Check rate on message_ack, user_message, reconnect
# Limit: 100 messages/min per user
```

### 7.3 Monitoring Setup

Prometheus metrics:

```python
from prometheus_client import Counter, Histogram

# Metrics
message_counter = Counter(
    'conversation_messages_total',
    'Total messages processed',
    ['message_type', 'status'],
)

replay_histogram = Histogram(
    'reconnect_replay_duration_seconds',
    'Reconnect replay duration',
)

context_truncation_counter = Counter(
    'context_truncation_total',
    'Context truncation events',
    ['reason'],
)
```

### 7.4 Backup & Retention

Scheduled jobs:

```python
# app/tasks/maintenance_tasks.py

@periodic_task(run_every=crontab(hour=2, minute=0))
def cleanup_old_reconnect_sessions():
    """Clean up reconnect sessions older than 24 hours."""
    from app.services.reconnect import ReconnectService
    from app.db.session import AsyncSessionLocal
    
    async def _task():
        db = AsyncSessionLocal()
        service = ReconnectService(db)
        deleted = await service.cleanup_old_reconnect_sessions(older_than_hours=24)
        logger.info(f"Cleaned {deleted} old reconnect sessions")
        await db.close()
    
    asyncio.run(_task())

@periodic_task(run_every=crontab(hour=1, minute=0))
def backup_conversations():
    """Backup conversations to cold storage."""
    # Export old conversations to S3/GCS
    pass
```

### 7.5 Security Audit

Checklist:

- [ ] All queries use parameterized statements
- [ ] All user input validated before DB use
- [ ] Tenant isolation verified at each layer
- [ ] PII encryption enabled for sensitive fields
- [ ] Rate limiting on reconnect endpoints
- [ ] Resume token TTL set (30 minutes)
- [ ] Message size limits enforced
- [ ] SQL injection tests pass
- [ ] XSS protection in responses
- [ ] CORS configured correctly

---

## Phase 8: Frontend Integration (Days 12-14)

### 8.1 WebSocket Client Wrapper

Frontend: `src/services/conversationClient.ts`

```typescript
export class ConversationClient {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Function[]> = new Map();
  private messageQueue: any[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  
  async connect(token: string, tenantId: string): Promise<void> {
    const url = `ws://api/v1/ws/stream/v2?token=${token}&tenant_id=${tenantId}`;
    
    this.ws = new WebSocket(url);
    
    this.ws.onopen = () => this.onOpen();
    this.ws.onmessage = (e) => this.onMessage(JSON.parse(e.data));
    this.ws.onerror = (e) => this.onError(e);
    this.ws.onclose = () => this.onClose();
  }
  
  private onMessage(data: any) {
    switch (data.type) {
      case "message_chunk":
        this.emit("chunk", data);
        break;
      case "message_complete":
        this.emit("complete", data);
        this.sendAck(data.message_id, data.sequence_no, data.total_chunks);
        break;
      case "error":
        this.emit("error", data);
        break;
      case "heartbeat":
        this.ws!.send(JSON.stringify({ type: "heartbeat_ack" }));
        break;
    }
  }
  
  async sendMessage(
    content: string,
    conversationId?: string
  ): Promise<string> {
    const messageId = uuid();
    
    this.ws!.send(JSON.stringify({
      type: "user_message",
      message_id: messageId,
      conversation_id: conversationId,
      content,
      language: "en",
    }));
    
    return messageId;
  }
  
  private sendAck(messageId: string, sequenceNo: number, lastChunk: number) {
    this.ws!.send(JSON.stringify({
      type: "message_ack",
      message_id: messageId,
      sequence_no: sequenceNo,
      last_chunk_no: lastChunk,
    }));
  }
  
  async reconnect(conversationId: string, lastSeqNo: number): Promise<void> {
    // Close existing and reconnect
    this.ws?.close();
    await this.connect(this.token!, this.tenantId!);
    
    // Request replay
    this.ws!.send(JSON.stringify({
      type: "reconnect",
      conversation_id: conversationId,
      last_sequence_no: lastSeqNo,
    }));
  }
}
```

### 8.2 React Hook

`src/hooks/useConversation.ts`:

```typescript
export function useConversation(token: string, tenantId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentResponse, setCurrentResponse] = useState("");
  const [conversationId, setConversationId] = useState<string>();
  const [isConnected, setIsConnected] = useState(false);
  const clientRef = useRef<ConversationClient>();
  
  useEffect(() => {
    const client = new ConversationClient();
    clientRef.current = client;
    
    client.on("connected", () => setIsConnected(true));
    client.on("chunk", (data) => {
      setCurrentResponse((prev) => prev + data.content);
    });
    client.on("complete", (data) => {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: "", sequence_no: data.sequence_no },
      ]);
      setCurrentResponse("");
    });
    
    client.connect(token, tenantId);
    
    return () => client.disconnect();
  }, [token, tenantId]);
  
  return {
    messages,
    currentResponse,
    conversationId,
    isConnected,
    sendMessage: (content: string) =>
      clientRef.current?.sendMessage(content, conversationId),
  };
}
```

---

## Testing Checklist

### Unit Tests

```bash
pytest tests/test_conversation_service.py -v
pytest tests/test_reconnect_service.py -v
pytest tests/test_vector_search.py -v
pytest tests/test_prompt_orchestrator.py -v
```

### Integration Tests

```bash
pytest tests/test_websocket_v2_integration.py -v
pytest tests/test_conversation_flow.py -v
pytest tests/test_reconnect_replay.py -v
```

### Load Tests

```bash
# Run with 100 concurrent WebSocket connections
locust -f tests/locustfile.py --host http://localhost:8000 -u 100 -r 10
```

---

## Deployment Steps

### Pre-Deployment

1. Run migrations in staging
2. Deploy new code (gateway_v2.py, services)
3. Run smoke tests
4. Monitor error rates
5. Verify database indexes

### Gradual Rollout

```bash
# Day 1: 10% traffic to v2
# Update load balancer config
upstream backend_v2 {
  server worker1:8000;  # 10% to v2
  server worker2:8000;  # 90% to v1
}

# Day 3: 50% traffic to v2
# Day 5: 100% traffic to v2
```

### Rollback Plan

```bash
# If issues detected, roll back to v1:
# 1. Update load balancer to 100% v1
# 2. Keep database changes (backward compatible)
# 3. Investigate v2 issues
# 4. Retry when fixed
```

---

## Monitoring Dashboard

Key metrics to dashboard:

1. **Connection Health**
   - Active connections by tenant
   - Connection duration distribution
   - Disconnect reasons

2. **Message Performance**
   - Messages/second
   - Average latency (send to first chunk)
   - Stream completion rate

3. **Context Building**
   - Truncation frequency
   - Token usage distribution
   - Semantic search latency

4. **Reconnect Activity**
   - Reconnect rate
   - Replay duration
   - Successful replay %

5. **Error Rates**
   - Errors by type
   - Error rate trend
   - Impacted tenants

---

## References

- [Stateful Conversation Architecture](./STATEFUL_CONVERSATION_ARCHITECTURE.md)
- [WebSocket Protocol V2](./WEBSOCKET_PROTOCOL_V2.md)
- [Database Schema](./alembic/versions/0014_add_stateful_conversation.py)
- [pgvector Docs](https://github.com/pgvector/pgvector)
- [FastAPI WebSocket Guide](https://fastapi.tiangolo.com/advanced/websockets/)
