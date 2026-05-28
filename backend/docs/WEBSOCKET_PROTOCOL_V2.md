# WebSocket Protocol Specification

**Version:** 2.0 (Stateful Conversation)  
**Endpoint:** `/api/v1/ws/stream/v2`  
**Query Parameters:**
- `token` (required): JWT access token
- `tenant_id` (optional): Explicit tenant ID override

---

## Message Types Reference

### Client → Server Messages

#### 1. **user_message** - Send new user query

```json
{
  "type": "user_message",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440001",
  "content": "What should I do for high blood pressure?",
  "language": "en",
  "metadata": {
    "voice_source": true,
    "sentiment": "concerned"
  }
}
```

**Required Fields:**
- `type`: "user_message"
- `content`: Non-empty message text

**Optional Fields:**
- `message_id`: Client-generated ID (server generates if omitted)
- `conversation_id`: Existing conversation (new if omitted)
- `language`: Language code (default: "en")
- `metadata`: Custom metadata dict

**Response Flow:**
1. `message_received` - Immediate ack
2. Multiple `message_chunk` events - Streaming chunks
3. `message_complete` - Final ack

---

#### 2. **message_ack** - Acknowledge received chunks

```json
{
  "type": "message_ack",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440001",
  "sequence_no": 42,
  "last_chunk_no": 5
}
```

**Required Fields:**
- `type`: "message_ack"
- `sequence_no`: Message sequence number
- `conversation_id`: Conversation ID
- `last_chunk_no`: Last chunk index received

**Purpose:**
- Tracks client progress for reconnect recovery
- Enables server to determine which chunks to replay

---

#### 3. **reconnect** - Resume after disconnect

```json
{
  "type": "reconnect",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440001",
  "last_sequence_no": 42,
  "resume_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Required Fields:**
- `type`: "reconnect"
- `conversation_id`: Conversation to resume

**Optional Fields:**
- `last_sequence_no`: Last known sequence (default: 0)
- `resume_token`: Previous resume token for validation

**Response:** `replay_start` followed by replay events, then `replay_complete`

---

#### 4. **ping** - Keep-alive from client

```json
{
  "type": "ping"
}
```

**Response:** `pong` message

---

#### 5. **heartbeat_ack** - Heartbeat acknowledgment

```json
{
  "type": "heartbeat_ack"
}
```

---

#### 6. **interrupt** - Interrupt response stream

```json
{
  "type": "interrupt",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "reason": "user_input"
}
```

---

### Server → Client Messages

#### 1. **auth_success** - Connection authenticated

```json
{
  "type": "auth_success",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "550e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440002",
  "message_id": "550e8400-e29b-41d4-a716-446655440003"
}
```

**Sent:** Immediately after successful authentication

---

#### 2. **message_received** - User message accepted

```json
{
  "type": "message_received",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440001",
  "sequence_no": 42
}
```

**Sent:** Immediately after processing user message

---

#### 3. **message_chunk** - Streaming response chunk

```json
{
  "type": "message_chunk",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "sequence_no": 43,
  "chunk_index": 0,
  "content": "You should consider reducing sodium intake and...",
  "delta_tokens": 15
}
```

**Fields:**
- `message_id`: ID of assistant response
- `sequence_no`: Global sequence number in conversation
- `chunk_index`: Index within this message (0, 1, 2...)
- `content`: Delta (new text in this chunk)
- `delta_tokens`: Token estimate for this chunk

**Sent:** Multiple times during streaming response

---

#### 4. **message_complete** - Response stream finished

```json
{
  "type": "message_complete",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "sequence_no": 43,
  "total_chunks": 12,
  "total_tokens": 215
}
```

**Sent:** Once per response after all chunks

---

#### 5. **replay_start** - Begin replay on reconnect

```json
{
  "type": "replay_start",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440001",
  "pending_messages": 2
}
```

**Sent:** When client requests reconnect and replay is available

---

#### 6. **replay_complete** - Replay finished

```json
{
  "type": "replay_complete",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Sent:** After all pending messages replayed

---

#### 7. **heartbeat** - Keep-alive from server

```json
{
  "type": "heartbeat",
  "session_id": "550e8400-e29b-41d4-a716-446655440001",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_id": "550e8400-e29b-41d4-a716-446655440003"
}
```

**Sent:** Every 30 seconds

**Expected Response:** `heartbeat_ack` or `pong`

---

#### 8. **pong** - Pong response

```json
{
  "type": "pong",
  "message_id": "550e8400-e29b-41d4-a716-446655440003"
}
```

**Sent:** In response to `ping`

---

#### 9. **error** - Error message

```json
{
  "type": "error",
  "error_code": "internal_error",
  "message": "Failed to process user message",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {
    "context": "additional_info"
  }
}
```

**Error Codes:**
- `missing_token`: No JWT token provided
- `invalid_token`: Token validation failed
- `missing_conversation_id`: Reconnect without conversation ID
- `invalid_resume_token`: Resume token invalid/expired
- `empty_message`: User message content is empty
- `unsupported_message_type`: Unknown message type
- `message_processing_failed`: Error processing user message
- `internal_error`: Unhandled server error

---

## Connection Lifecycle

### Happy Path: New Conversation

```
Client                          Server                   Database
  |                               |                         |
  |------- Connect + JWT -------->|                         |
  |                             (auth)                       |
  |                               |----------- Query ------->|
  |                               |<---- User/Session ------|
  |<----- auth_success -----------|                         |
  |                               |                         |
  |--- user_message("hi") ------->|                         |
  |                               |---- Create Conversation |
  |<----- message_received -------|---------> Store ------->|
  |                               |                         |
  |                               |---- Build context ------|
  |                               |<--- Recent messages ----|
  |                               |                         |
  |<----- message_chunk ---------|                         |
  |                          (streaming)                    |
  |<----- message_chunk ---------|                         |
  |                               |---- Save chunks ------->|
  |<----- message_chunk ---------|---------> Store ------->|
  |                               |                         |
  |<----- message_complete -------|                         |
  |                               |---- Save message -------|
  |                               |---------> Store ------->|
  |                               |                         |
  |--- message_ack ------->|                         |
  |                               |---- Update reconnect ----|
  |                               |---------> Update ------>|
  |                               |                         |
```

### Reconnect Path

```
Client                          Server                   Database
  |                               |                         |
  |---- Disconnect ----           |                         |
  |     (e.g., network)           |                         |
  |                               | (Keep-alive timeout)    |
  |---- Connect + JWT ------>|                         |
  |<----- auth_success -----------|                         |
  |                               |                         |
  |--- reconnect(last_seq=42)--->|                         |
  |                               |---- Query replay ------>|
  |                               |<--- Unacked messages ----|
  |                               |                         |
  |<----- replay_start -------------|                         |
  |<----- message_chunk ---------|  (seq 43)               |
  |<----- message_chunk ---------|  (seq 43)               |
  |<----- message_complete -------|  (seq 43)               |
  |<----- message_chunk ---------|  (seq 44)               |
  |<----- message_complete -------|  (seq 44)               |
  |<----- replay_complete ---------|                         |
  |                               |                         |
  |--- message_ack ------->|                         |
  |                               |---- Update tracking ----|
  |                               |---------> Update ------>|
  |                               |                         |
```

---

## Error Scenarios & Recovery

### Scenario 1: Message Interrupted Mid-Stream

```
Client sends: user_message("What about...?")
Server streams: chunk 0, chunk 1, chunk 2...
Client sends: interrupt

Server:
- Stops streaming
- Marks message as incomplete
- Saves partial content
- Sends stream_interrupted event

On Reconnect:
- Client requests replay from last_acked
- Server replays incomplete message chunks
- Client can retry or continue
```

### Scenario 2: Network Disconnect During Stream

```
Server sends: message_chunk (seq 43, chunk 3)
Client: [Network breaks - doesn't receive]

Client reconnects:
- Sends: reconnect(last_sequence_no=42)
- Server: Finds unacked messages (seq 43)
- Server: Replays chunks starting from chunk 0 of seq 43
- Client: Receives full message including chunk 3
- Client: Sends message_ack(seq=43, last_chunk=10)
```

### Scenario 3: Token Expiry

```
Client sends: user_message("...")
Server receives valid message
Processing takes 10 seconds...
Token expires while streaming

Server:
- Continues streaming (token valid at receive time)
- Marks message as complete

Client reconnects with new token:
- Sends: reconnect(conversation_id, last_seq)
- Receives all pending messages (already saved)
```

---

## Performance Considerations

### Token Budget Management

Prompt context is built with token limits:
```
Total Budget: 2000 tokens
├─ System Prompt: ~100 tokens
├─ User Context: ~100 tokens  
├─ Current Message: ~50 tokens
├─ Reserved for Response: ~500 tokens (25%)
└─ Available for History: ~1250 tokens
    ├─ Recent Messages: ~1000 tokens
    ├─ Semantic Memories: ~250 tokens
    └─ Summarized History: fallback
```

### Reconnect Efficiency

Replay is optimized:
- Only unsent/unacked chunks replayed
- Chunks stored in database (no re-generation)
- Replay is O(n) where n = unacked messages
- Typical replay: <50ms for 5 messages

---

## Security & Validation

### Message Validation

Every message validates:
1. JWT token integrity
2. Tenant isolation (tenant_id in token must match)
3. Session validity (revoked check)
4. User ownership (user_id match)
5. Conversation ownership (user_id or org_id)
6. Rate limiting (max messages/sec per user)

### Reconnect Security

Resume tokens include:
```json
{
  "sub": "session_id",
  "tenant_id": "...",
  "conversation_id": "...",
  "last_acked_message_no": 42,
  "exp": "2026-05-26T15:30:00Z",
  "type": "resume"
}
```

Validation:
- Token signature verified
- Expiry checked (default: 30 minutes)
- Type field = "resume" required
- Claims must match current request

---

## Client Implementation Guide

### Pseudo-code: Basic Handler

```javascript
class ConversationClient {
  async connect(token, tenantId) {
    this.ws = new WebSocket(
      `ws://api/v1/ws/stream/v2?token=${token}&tenant_id=${tenantId}`
    );
    
    this.ws.onmessage = this.handleMessage.bind(this);
    this.ws.onerror = this.handleError.bind(this);
    this.ws.onclose = this.handleDisconnect.bind(this);
  }
  
  async sendMessage(content, conversationId = null) {
    this.ws.send(JSON.stringify({
      type: "user_message",
      content: content,
      conversation_id: conversationId,
      language: "en"
    }));
  }
  
  handleMessage(event) {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
      case "message_chunk":
        this.appendToDisplay(data.content);
        this.recordAck(data.message_id, data.sequence_no, data.chunk_index);
        break;
      
      case "message_complete":
        this.confirmMessageComplete(data.sequence_no);
        break;
      
      case "error":
        this.showError(data.message);
        break;
      
      case "heartbeat":
        this.ws.send(JSON.stringify({ type: "heartbeat_ack" }));
        break;
    }
  }
  
  recordAck(messageId, sequenceNo, chunkNo) {
    // Send ack after processing (batched per second)
    this.pendingAck = { messageId, sequenceNo, chunkNo };
  }
  
  async reconnect(conversationId, lastSeqNo, resumeToken) {
    await this.connect(this.token, this.tenantId);
    
    this.ws.send(JSON.stringify({
      type: "reconnect",
      conversation_id: conversationId,
      last_sequence_no: lastSeqNo,
      resume_token: resumeToken
    }));
  }
}
```

---

## Monitoring & Observability

### Key Metrics to Track

- Connection count by tenant
- Message latency (user input to first chunk)
- Stream completion rate
- Reconnect frequency
- Chunk size distribution
- Error rate by type
- Context truncation frequency
- Vector search latency

### Logging

All events logged with:
```json
{
  "timestamp": "2026-05-26T14:30:00.000Z",
  "level": "INFO",
  "event": "message_complete",
  "conversation_id": "...",
  "session_id": "...",
  "user_id": "...",
  "duration_ms": 1250,
  "chunk_count": 12,
  "context_sources": ["recent_messages", "semantic_memories"]
}
```
