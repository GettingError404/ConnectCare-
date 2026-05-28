"""Enhanced WebSocket gateway with stateful conversation support.

Features:
- Conversation ID tracking
- Message acknowledgment protocol
- Reconnect and replay handling
- Contextualized prompt building
- Stream reliability
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.websocket.auth import authenticate_websocket
from app.websocket.manager import ConnectionManager
from app.db.session import get_async_db
from app.services.conversation_context import ConversationContextService
from app.services.reconnect import ReconnectService
from app.services.prompt_orchestrator import PromptOrchestratorService
from app.services.vector_search import VectorSearchService
from app.models.conversation import ConversationThread, StreamingChunk
from app.models.ai_memory import AIMessage
from app.db.base import UUIDPrimaryKeyMixin
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

manager = ConnectionManager()


def _msg_id() -> str:
    """Generate a unique message ID."""
    return str(uuid.uuid4())


@router.websocket("/ws/stream/v2")
async def ws_stream_v2(
    websocket: WebSocket,
    token: str = Query(None),
    tenant_id: str = Query(None),
):
    """Enhanced WebSocket endpoint with stateful conversation support.
    
    Protocol:
    1. Client connects with JWT token
    2. Server authenticates and validates session
    3. Client can send:
       - user_message: start new message in conversation
       - message_ack: acknowledge received chunks
       - reconnect: resume after disconnect
       - ping/heartbeat: keep-alive
    4. Server sends:
       - auth_success: connection established
       - message_chunk: incremental response chunks
       - message_complete: response finished
       - replay_start: begin replay on reconnect
       - heartbeat: keep-alive from server
       - error: error events
    """
    if not token:
        await websocket.close(code=4001, reason="missing_token")
        return

    user = None
    t_id: Optional[UUID] = None
    s_id: Optional[UUID] = None
    db_session: Optional[AsyncSession] = None

    try:
        # Authenticate WebSocket
        user, t_id, s_id = await authenticate_websocket(
            websocket=websocket,
            token=token,
            tenant_id=tenant_id,
        )
        
        assert t_id is not None and s_id is not None

        # Get database session for this connection
        db_session = get_async_db()
        
        # Register connection
        await manager.connect(tenant_id=t_id, user_id=user.id, session_id=s_id, websocket=websocket)

        # Send auth success
        await websocket.send_json({
            "type": "auth_success",
            "tenant_id": str(t_id),
            "session_id": str(s_id),
            "user_id": str(user.id),
            "message_id": _msg_id(),
        })

        # Initialize services
        context_service = ConversationContextService(db_session)
        reconnect_service = ReconnectService(db_session)
        vector_service = VectorSearchService(db_session)
        prompt_orchestrator = PromptOrchestratorService(
            db_session=db_session,
            context_service=context_service,
            vector_service=vector_service,
        )

        # Heartbeat coroutine
        async def heartbeat_loop() -> None:
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "session_id": str(s_id),
                        "tenant_id": str(t_id),
                        "message_id": _msg_id(),
                    })
                except Exception:
                    return

        hb_task = asyncio.create_task(heartbeat_loop())

        # Redis subscription for agent events
        redis_sub_task: Optional[asyncio.Task] = None
        try:
            from app.events.redis_pubsub import RedisPubSub, conversation_channel

            redis_bus = RedisPubSub()
            stop_event = asyncio.Event()
            channel = conversation_channel(t_id, s_id)

            async def _on_redis_message(evt: dict) -> None:
                # Validate event is for this session
                if str(evt.get("tenant_id")) != str(t_id) and evt.get("tenant_id"):
                    return
                if str(evt.get("session_id")) != str(s_id) and evt.get("session_id"):
                    return

                await websocket.send_json(evt)

            redis_sub_task = asyncio.create_task(
                redis_bus.subscribe_forever(
                    channels=[channel],
                    on_message=_on_redis_message,
                    stop_event=stop_event,
                )
            )
        except Exception as e:
            logger.warning("redis_subscription_setup_failed", extra={"error": str(e)})

        # Main message processing loop
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            # --- Heartbeat/Keep-Alive ---
            if msg_type in ("pong", "heartbeat_ack"):
                await manager.mark_heartbeat(websocket)
                continue

            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "message_id": _msg_id(),
                })
                continue

            # --- User Message ---
            if msg_type == "user_message":
                await _handle_user_message(
                    websocket=websocket,
                    data=data,
                    tenant_id=t_id,
                    user_id=user.id,
                    session_id=s_id,
                    db_session=db_session,
                    prompt_orchestrator=prompt_orchestrator,
                    reconnect_service=reconnect_service,
                )
                continue

            # --- Message Acknowledgment ---
            if msg_type == "message_ack":
                await _handle_message_ack(
                    websocket=websocket,
                    data=data,
                    tenant_id=t_id,
                    user_id=user.id,
                    session_id=s_id,
                    reconnect_service=reconnect_service,
                )
                continue

            # --- Reconnect/Replay ---
            if msg_type == "reconnect":
                await _handle_reconnect(
                    websocket=websocket,
                    data=data,
                    tenant_id=t_id,
                    session_id=s_id,
                    reconnect_service=reconnect_service,
                )
                continue

            # --- Interrupt ---
            if msg_type == "interrupt":
                await websocket.send_json({
                    "type": "session_update",
                    "tenant_id": str(t_id),
                    "session_id": str(s_id),
                    "message": "interruption_acknowledged",
                    "message_id": _msg_id(),
                })
                continue

            # --- Unknown message type ---
            await websocket.send_json({
                "type": "error",
                "error_code": "unsupported_message_type",
                "message": f"Unknown message type: {msg_type}",
                "message_id": _msg_id(),
            })

    except WebSocketDisconnect:
        logger.info("ws_disconnect", extra={"user_id": str(user.id) if user else None})
    except Exception as e:
        logger.exception("ws_stream_error")
        try:
            await websocket.send_json({
                "type": "error",
                "error_code": "internal_error",
                "message": str(e),
                "message_id": _msg_id(),
            })
        except Exception:
            pass
    finally:
        if user is not None and t_id is not None and s_id is not None:
            await manager.disconnect(
                tenant_id=t_id,
                user_id=user.id,
                session_id=s_id,
                websocket=websocket,
            )
        
        if db_session:
            await db_session.close()


async def _handle_user_message(
    websocket: WebSocket,
    data: dict,
    tenant_id: UUID,
    user_id: UUID,
    session_id: UUID,
    db_session: AsyncSession,
    prompt_orchestrator: PromptOrchestratorService,
    reconnect_service: ReconnectService,
) -> None:
    """Handle incoming user message.
    
    Protocol:
    {
      "type": "user_message",
      "conversation_id": "uuid",  // Required or create new
      "content": "What should I do?",
      "language": "en",
      "metadata": {...}
    }
    """
    message_id = data.get("message_id") or _msg_id()
    conversation_id_str = data.get("conversation_id")
    content = data.get("content") or ""
    language = data.get("language", "en")
    metadata = data.get("metadata", {})

    if not content:
        await websocket.send_json({
            "type": "error",
            "error_code": "empty_message",
            "message": "Message content cannot be empty",
            "message_id": message_id,
        })
        return

    try:
        # Get or create conversation
        conversation_id: Optional[UUID] = None
        if conversation_id_str:
            try:
                conversation_id = UUID(str(conversation_id_str))
            except ValueError:
                pass
        
        # Get database session and create conversation if needed
        context_service = ConversationContextService(db_session)
        
        if not conversation_id:
            # Create new conversation thread
            conversation_id = UUIDPrimaryKeyMixin.generate_id()
            conversation = ConversationThread(
                id=conversation_id,
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                title=content[:100],  # Auto-generate title
                status="active",
                metadata_json={"language": language},
            )
            db_session.add(conversation)
            await db_session.flush()
            
            logger.info("conversation_created", extra={"conversation_id": str(conversation_id)})
        
        # Create reconnect session
        reconnect_session = await reconnect_service.create_or_get_reconnect_session(
            tenant_id=tenant_id,
            session_id=session_id,
            conversation_id=conversation_id,
        )
        
        # Calculate next message sequence number
        from sqlalchemy import select, func
        count_stmt = select(func.count(AIMessage.id)).where(
            AIMessage.conversation_id == conversation_id
        )
        result = await db_session.execute(count_stmt)
        next_sequence_no = (result.scalar() or 0) + 1
        
        # Save user message
        user_msg = AIMessage(
            id=UUIDPrimaryKeyMixin.generate_id(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role="user",
            content=content,
            content_hash="",  # TODO: compute hash
            sequence_no=next_sequence_no,
            is_streaming=False,
            stream_complete=True,
            token_count=len(content.split()),  # Rough estimate
            recorded_at=datetime.utcnow(),
            metadata_json=metadata,
        )
        db_session.add(user_msg)
        await db_session.flush()
        
        # Send user message received ack
        await websocket.send_json({
            "type": "message_received",
            "message_id": message_id,
            "conversation_id": str(conversation_id),
            "sequence_no": next_sequence_no,
        })
        
        # Build optimized prompt using services
        orchestrated_prompt = await prompt_orchestrator.orchestrate_prompt(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            user_message=content,
        )
        
        # Connect to agent and stream response
        from app.agent.connectors.agent_connector import AgentConnector, AgentStreamRequest
        from app.events.redis_pubsub import RedisPubSub
        
        redis_pubsub = RedisPubSub()
        connector = AgentConnector(
            agent_ws_url=str(getattr(settings, "AGENT_WS_URL", "ws://agent:8000/ws/stream")),
            redis_pubsub=redis_pubsub,
        )
        
        # Prepare agent request
        req = AgentStreamRequest(
            tenant_id=str(tenant_id),
            session_id=str(session_id),
            message_id=message_id,
            content=content,
            language=language,
            # Include prompt context in request
            system_prompt=orchestrated_prompt["system_prompt"],
            context_messages=orchestrated_prompt["messages"],
        )
        
        # Create assistant message
        assistant_msg_id = UUIDPrimaryKeyMixin.generate_id()
        assistant_msg = AIMessage(
            id=assistant_msg_id,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role="assistant",
            content="",  # Will be filled from chunks
            content_hash="",
            sequence_no=next_sequence_no + 1,
            is_streaming=True,
            stream_complete=False,
            recorded_at=datetime.utcnow(),
        )
        db_session.add(assistant_msg)
        await db_session.flush()
        
        # Stream chunks from agent
        chunk_index = 0
        full_content = ""
        async for chunk_evt in connector.stream_text(req):
            # Save streaming chunk
            if chunk_evt.get("type") == "message_chunk":
                chunk_content = chunk_evt.get("content", "")
                full_content += chunk_content
                
                streaming_chunk = StreamingChunk(
                    id=UUIDPrimaryKeyMixin.generate_id(),
                    tenant_id=tenant_id,
                    message_id=assistant_msg_id,
                    sequence_no=next_sequence_no + 1 + chunk_index,
                    chunk_index=chunk_index,
                    content=chunk_content,
                    delta_tokens=chunk_evt.get("delta_tokens"),
                )
                db_session.add(streaming_chunk)
                await db_session.flush()
                
                chunk_index += 1
            
            # Send to client
            await websocket.send_json(chunk_evt)
        
        # Update assistant message with full content
        assistant_msg.content = full_content
        assistant_msg.stream_complete = True
        assistant_msg.is_streaming = False
        await db_session.flush()
        await db_session.commit()
        
        # Send stream complete
        await websocket.send_json({
            "type": "message_complete",
            "message_id": message_id,
            "sequence_no": next_sequence_no + 1,
            "total_chunks": chunk_index,
            "total_tokens": len(full_content.split()),
        })
        
        logger.info("message_stream_complete", extra={"conversation_id": str(conversation_id)})
        
    except Exception as e:
        logger.exception("user_message_handling_failed")
        await websocket.send_json({
            "type": "error",
            "error_code": "message_processing_failed",
            "message": str(e),
            "message_id": message_id,
        })


async def _handle_message_ack(
    websocket: WebSocket,
    data: dict,
    tenant_id: UUID,
    user_id: UUID,
    session_id: UUID,
    reconnect_service: ReconnectService,
) -> None:
    """Handle client message acknowledgment.
    
    Protocol:
    {
      "type": "message_ack",
      "message_id": "uuid",
      "sequence_no": 42,
      "last_chunk_no": 5
    }
    """
    message_id = data.get("message_id")
    sequence_no = data.get("sequence_no")
    last_chunk_no = data.get("last_chunk_no", 0)
    conversation_id_str = data.get("conversation_id")

    if not message_id or not sequence_no or not conversation_id_str:
        await websocket.send_json({
            "type": "error",
            "error_code": "invalid_ack",
            "message": "Missing required ack fields",
        })
        return

    try:
        conversation_id = UUID(str(conversation_id_str))
        
        await reconnect_service.record_message_acknowledgment(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            user_id=user_id,
            session_id=session_id,
            message_sequence_no=sequence_no,
            last_chunk_sequence_no=last_chunk_no,
        )
        
        logger.debug("message_acked", extra={"sequence_no": sequence_no})
        
    except Exception as e:
        logger.warning("ack_handling_failed", extra={"error": str(e)})


async def _handle_reconnect(
    websocket: WebSocket,
    data: dict,
    tenant_id: UUID,
    session_id: UUID,
    reconnect_service: ReconnectService,
) -> None:
    """Handle reconnect request with replay.
    
    Protocol:
    {
      "type": "reconnect",
      "conversation_id": "uuid",
      "last_sequence_no": 42,
      "resume_token": "jwt"
    }
    """
    conversation_id_str = data.get("conversation_id")
    last_sequence_no = data.get("last_sequence_no", 0)
    resume_token = data.get("resume_token")

    if not conversation_id_str:
        await websocket.send_json({
            "type": "error",
            "error_code": "missing_conversation_id",
        })
        return

    try:
        conversation_id = UUID(str(conversation_id_str))
        
        # Validate resume token if provided
        if resume_token:
            token_payload = await reconnect_service.validate_resume_token(resume_token)
            if not token_payload:
                await websocket.send_json({
                    "type": "error",
                    "error_code": "invalid_resume_token",
                })
                return
            last_sequence_no = token_payload.get("last_acked_message_no", last_sequence_no)
        
        # Get pending replay
        replay_events = await reconnect_service.get_pending_replay(
            tenant_id=tenant_id,
            session_id=session_id,
            conversation_id=conversation_id,
            from_sequence_no=last_sequence_no,
        )
        
        # Send replay
        await websocket.send_json({
            "type": "replay_start",
            "conversation_id": str(conversation_id),
            "pending_messages": len(replay_events),
        })
        
        # Stream replay events
        for evt in replay_events:
            await websocket.send_json(evt)
        
        await websocket.send_json({
            "type": "replay_complete",
            "conversation_id": str(conversation_id),
        })
        
        logger.info("replay_sent", extra={"events": len(replay_events)})
        
    except Exception as e:
        logger.exception("reconnect_handling_failed")
        await websocket.send_json({
            "type": "error",
            "error_code": "reconnect_failed",
            "message": str(e),
        })
