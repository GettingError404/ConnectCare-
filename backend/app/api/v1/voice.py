from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.websocket.auth import authenticate_websocket
from app.services.conversation_context import ConversationContextService
from app.agent.connectors.agent_connector import AgentConnector, AgentStreamRequest
from app.db.base import UUIDPrimaryKeyMixin
from app.models.ai_memory import AIMessage, StreamingChunk
from app.models.conversation import ConversationThread

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice")


@router.post('/start')
async def start_voice_session():
    """Create new conversation/session identifiers."""
    cid = UUIDPrimaryKeyMixin.generate_id()
    sid = UUIDPrimaryKeyMixin.generate_id()
    return {"conversation_id": str(cid), "session_id": str(sid)}


@router.post('/transcribe')
async def transcribe_audio(audio_b64: str = Body(..., embed=True), language: str = 'en'):
    """Transcribe base64-encoded audio bytes using agent STT pipeline."""
    try:
        audio_bytes = base64.b64decode(audio_b64)
        # import agent STT
        from agent.pipeline.stt import SpeechToText
        from agent.config.settings import STTSettings

        stt = SpeechToText(STTSettings())
        result = await stt.transcribe(audio_bytes, language=language)
        return {"text": result.text, "confidence": result.confidence, "source": result.source}
    except Exception as e:
        logger.exception('transcribe_failed')
        return {"text": "", "confidence": 0.0, "error": str(e)}


@router.post('/respond')
async def respond(
    conversation_id: Optional[str] = Body(None),
    session_id: Optional[str] = Body(None),
    content: str = Body(...),
    language: str = Body('en'),
):
    """Synchronous respond endpoint that calls the agent and returns final text."""
    db: AsyncSession = get_async_db()
    try:
        # Build prompt context
        context_service = ConversationContextService(db)
        orchestrated = await context_service.build_optimized_context(
            tenant_id=UUID(session_id) if session_id else UUIDPrimaryKeyMixin.generate_id(),
            conversation_id=UUID(conversation_id) if conversation_id else UUIDPrimaryKeyMixin.generate_id(),
            current_message=content,
        )

        connector = AgentConnector(agent_ws_url='ws://agent:8000/ws/stream')
        req = AgentStreamRequest(
            tenant_id=str(session_id or ''),
            session_id=str(session_id or ''),
            message_id=str(UUIDPrimaryKeyMixin.generate_id()),
            content=content,
            language=language,
        )

        full = ''
        async for evt in connector.stream_text(req):
            if evt.get('type') == 'agent_chunk':
                full += evt.get('content', '')
            if evt.get('type') == 'agent_final':
                full += evt.get('content', '')
                break

        return {"response": full}
    finally:
        await db.close()


@router.post('/speak')
async def speak_text(text: str = Body(...), language: str = Body('en')):
    """Synthesize text to audio and return base64-encoded bytes."""
    try:
        from agent.pipeline.tts import TextToSpeech
        from agent.config.settings import Settings as AgentSettings

        tts = TextToSpeech(AgentSettings().tts)
        audio = await tts.synthesize(text, language=language)
        b64 = base64.b64encode(audio.audio_bytes).decode('ascii') if audio.audio_bytes else ''
        return {"audio_b64": b64, "backend": audio.backend, "format": audio.format}
    except Exception as e:
        logger.exception('tts_failed')
        return {"audio_b64": '', "error": str(e)}


@router.websocket('/ws')
async def ws_voice(
    websocket: WebSocket,
    token: str = Query(None),
    tenant_id: str = Query(None),
):
    """Realtime voice websocket. Accepts audio chunks and user messages, streams agent responses and tts audio."""
    if not token:
        await websocket.close(code=4001, reason='missing_token')
        return

    user = None
    db: Optional[AsyncSession] = None

    try:
        user, t_id, s_id = await authenticate_websocket(websocket=websocket, token=token, tenant_id=tenant_id)
        db = get_async_db()

        stt = None
        tts = None
        try:
            from agent.pipeline.stt import SpeechToText
            from agent.config.settings import STTSettings, Settings as AgentSettings
            from agent.pipeline.tts import TextToSpeech

            stt = SpeechToText(STTSettings())
            tts = TextToSpeech(AgentSettings().tts)
        except Exception:
            logger.exception('stt_tts_init_failed')

        await websocket.accept()

        audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        transcribing = True

        async def transcribe_loop():
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    break
                try:
                    if stt:
                        result = await stt.transcribe(chunk)
                        await websocket.send_json({
                            'type': 'transcription',
                            'conversation_id': None,
                            'session_id': str(s_id),
                            'payload': {'text': result.text, 'confidence': result.confidence, 'source': result.source}
                        })
                except Exception:
                    logger.exception('transcribe_error')

        transcribe_task = asyncio.create_task(transcribe_loop())

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                await websocket.send_json({'type': 'error', 'conversation_id': None, 'session_id': str(s_id), 'payload': {'message': 'invalid_json'}})
                continue

            ev_type = data.get('type')
            conv = data.get('conversation_id')
            sess = data.get('session_id')
            payload = data.get('payload') or {}

            if ev_type == 'user_audio_chunk':
                b64 = payload.get('audio_b64')
                if not b64:
                    continue
                try:
                    audio_bytes = base64.b64decode(b64)
                    await audio_queue.put(audio_bytes)
                except Exception:
                    logger.exception('audio_decode_failed')
                    await websocket.send_json({'type': 'error', 'conversation_id': conv, 'session_id': sess, 'payload': {'message': 'invalid_audio'}})
                continue

            if ev_type == 'start_conversation':
                # create conversation thread if needed
                try:
                    cid = conv or str(UUIDPrimaryKeyMixin.generate_id())
                    conversation = ConversationThread(
                        id=UUIDPrimaryKeyMixin.generate_id(),
                        tenant_id=t_id,
                        user_id=user.id,
                        session_id=s_id,
                        title=payload.get('title', 'Voice Conversation')[:100],
                        status='active',
                    )
                    db.add(conversation)
                    await db.flush()
                    await websocket.send_json({'type': 'conversation_started', 'conversation_id': str(conversation.id), 'session_id': str(s_id), 'payload': {}})
                except Exception:
                    logger.exception('start_conversation_failed')
                continue

            if ev_type == 'user_message':
                # call agent and stream
                content = payload.get('text') or ''
                if not content:
                    await websocket.send_json({'type': 'error', 'conversation_id': conv, 'session_id': sess, 'payload': {'message': 'empty_message'}})
                    continue

                # build context
                context_service = ConversationContextService(db)
                orchestrated = await context_service.build_optimized_context(
                    tenant_id=t_id,
                    conversation_id=UUID(conv) if conv else UUIDPrimaryKeyMixin.generate_id(),
                    current_message=content,
                )

                connector = AgentConnector(agent_ws_url=str('ws://agent:8000/ws/stream'))
                req = AgentStreamRequest(
                    tenant_id=str(t_id),
                    session_id=str(s_id),
                    message_id=str(UUIDPrimaryKeyMixin.generate_id()),
                    content=content,
                    language=payload.get('language', 'en'),
                )

                # stream agent response
                async for evt in connector.stream_text(req):
                    if evt.get('type') == 'typing_start':
                        await websocket.send_json({'type': 'agent_thinking', 'conversation_id': conv, 'session_id': sess, 'payload': {}})
                    if evt.get('type') == 'agent_chunk':
                        await websocket.send_json({'type': 'agent_response', 'conversation_id': conv, 'session_id': sess, 'payload': {'content': evt.get('content'), 'is_final': evt.get('is_final', False)}})
                    if evt.get('type') == 'agent_final':
                        final_text = evt.get('content', '')
                        await websocket.send_json({'type': 'agent_response', 'conversation_id': conv, 'session_id': sess, 'payload': {'content': final_text, 'is_final': True}})
                        # synthesize audio and stream TTS in chunks
                        if tts:
                            audio = await tts.synthesize(final_text)
                            if audio and audio.audio_bytes:
                                chunk_size = 16000
                                b = audio.audio_bytes
                                for i in range(0, len(b), chunk_size):
                                    part = b[i:i+chunk_size]
                                    await websocket.send_json({'type': 'tts_audio_chunk', 'conversation_id': conv, 'session_id': sess, 'payload': {'audio_b64': base64.b64encode(part).decode('ascii'), 'is_last': i+chunk_size >= len(b)}})
                        break

                continue

            if ev_type == 'stop_conversation':
                # signal audio transcriber to stop
                await audio_queue.put(None)
                await websocket.send_json({'type': 'conversation_stopped', 'conversation_id': conv, 'session_id': sess, 'payload': {}})
                continue

            if ev_type == 'ping':
                await websocket.send_json({'type': 'pong', 'conversation_id': conv, 'session_id': sess, 'payload': {}})
                continue

            await websocket.send_json({'type': 'error', 'conversation_id': conv, 'session_id': sess, 'payload': {'message': 'unsupported_event'}})

    except WebSocketDisconnect:
        logger.info('voice_ws_disconnect')
    except Exception:
        logger.exception('voice_ws_error')
    finally:
        try:
            if db:
                await db.close()
        except Exception:
            pass
