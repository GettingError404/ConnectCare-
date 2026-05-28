from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.websocket.auth import authenticate_websocket
from app.websocket.manager import ConnectionManager

router = APIRouter()
logger = logging.getLogger(__name__)

manager = ConnectionManager()


def _msg_id() -> str:
    return str(uuid.uuid4())


@router.websocket("/ws/stream")
async def ws_stream(
    websocket: WebSocket,
    token: str = Query(None),
    tenant_id: str = Query(None),
):
    if not token:
        await websocket.close(code=4001)
        return

    user = None
    t_id: Optional[UUID] = None
    s_id: Optional[UUID] = None

    try:
        user, t_id, s_id = await authenticate_websocket(
            websocket=websocket,
            token=token,
            tenant_id=tenant_id,
        )

        assert t_id is not None and s_id is not None

        await manager.connect(tenant_id=t_id, user_id=user.id, session_id=s_id, websocket=websocket)

        await websocket.send_json({
            "type": "auth_success",
            "tenant_id": str(t_id),
            "session_id": str(s_id),
            "user_id": str(user.id),
            "message_id": _msg_id(),
        })

        # Heartbeat loop
        async def heartbeat() -> None:
            while True:
                await asyncio.sleep(20)
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "session_id": str(s_id),
                        "tenant_id": str(t_id),
                        "message_id": _msg_id(),
                    })
                except Exception:
                    return

        hb_task = asyncio.create_task(heartbeat())

        # Subscribe to redis conversation channel for this session (agent chunks, alerts, etc.)
        redis_sub_task: Optional[asyncio.Task] = None
        try:
            from app.events.redis_pubsub import RedisPubSub, conversation_channel

            redis_bus = RedisPubSub()
            stop_event = asyncio.Event()
            channel = conversation_channel(t_id, s_id)

            async def _on_redis_message(evt: dict[str, object]) -> None:
                # evt is expected to be already gateway-compatible (agent_chunk/alert_event/etc.)
                # Add basic session scoping guard.
                if str(evt.get("tenant_id")) != str(t_id) and evt.get("tenant_id") is not None:
                    return
                if str(evt.get("session_id")) != str(s_id) and evt.get("session_id") is not None:
                    return

                await websocket.send_json(evt)

            redis_sub_task = asyncio.create_task(
                redis_bus.subscribe_forever(
                    channels=[channel],
                    on_message=_on_redis_message,
                    stop_event=stop_event,
                )
            )
        except Exception:
            logger.exception("redis_subscription_setup_failed")
            redis_sub_task = None

        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")


            if msg_type == "pong" or msg_type == "heartbeat_ack":
                await manager.mark_heartbeat(websocket)
                continue

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "message_id": _msg_id()})
                continue

            if msg_type == "user_message":
                # Required input type: {type:"user_message", message_id, content, language?}
                from app.agent.connectors.agent_connector import AgentConnector, AgentStreamRequest
                from app.core.config import settings

                message_id = data.get("message_id") or _msg_id()
                content = data.get("content") or ""
                language = data.get("language")

                # Connect to agent and stream mapped events back to the client.
                from app.events.redis_pubsub import RedisPubSub

                redis_pubsub = RedisPubSub()
                connector = AgentConnector(
                    agent_ws_url=str(getattr(settings, "AGENT_WS_URL", "ws://agent:8000/ws/stream")),
                    redis_pubsub=redis_pubsub,
                )

                req = AgentStreamRequest(
                    tenant_id=str(t_id),
                    session_id=str(s_id),
                    message_id=message_id,
                    content=content,
                    language=language,
                )

                async for evt in connector.stream_text(req):
                    await websocket.send_json(evt)
                continue

            if msg_type == "interrupt":
                await websocket.send_json({
                    "type": "session_update",
                    "tenant_id": str(t_id),
                    "session_id": str(s_id),
                    "message": "interruption acknowledged",
                    "message_id": _msg_id(),
                })
                continue

            # Reconnect protocol placeholder
            if msg_type == "reconnect":
                # Next step: replay persisted events from sequence number
                await websocket.send_json({
                    "type": "reconnect",
                    "tenant_id": str(t_id),
                    "session_id": str(s_id),
                    "status": "replay_not_implemented",
                    "message_id": _msg_id(),
                })
                continue

            await websocket.send_json({
                "type": "error",
                "tenant_id": str(t_id),
                "session_id": str(s_id) if s_id else None,
                "message": f"unsupported_message_type: {msg_type}",
                "message_id": _msg_id(),
            })

    except WebSocketDisconnect:
        logger.info("ws_disconnect", extra={"tenant_id": tenant_id, "token_present": bool(token)})
    except Exception as e:
        logger.exception("ws_stream_error")
        try:
            await websocket.send_json({"type": "error", "error": str(e), "message_id": _msg_id()})
        except Exception:
            pass
    finally:
        if user is not None and t_id is not None and s_id is not None:
            await manager.disconnect(tenant_id=t_id, user_id=user.id, session_id=s_id, websocket=websocket)

