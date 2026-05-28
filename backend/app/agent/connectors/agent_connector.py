from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator

import websockets

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentStreamRequest:
    tenant_id: str
    session_id: str
    message_id: str
    content: str
    language: str | None = None


class AgentConnector:
    """Bridges backend websocket contract to the agent service websocket protocol.

    Current agent service (agent/api.py) is stage-based:
      - client -> agent: {"type": "text", "text": ..., "language": ...}
      - agent -> backend: {"stage": "started" | "complete" | <other stages>, ...}

    Emits gateway events:
      - typing_start
      - agent_chunk (intermediate + final chunk)
      - agent_final

    If a `redis_pubsub` is provided, every emitted gateway event is also published to:
      - conversation:{tenant_id}:{session_id}
    """

    def __init__(self, *, agent_ws_url: str, redis_pubsub: Any | None = None):
        self._agent_ws_url = agent_ws_url
        self._redis_pubsub = redis_pubsub

    async def _maybe_publish(self, *, channel: str, event: dict[str, Any]) -> None:
        if not self._redis_pubsub:
            return
        try:
            await self._redis_pubsub.publish(channel, event)
        except Exception:
            logger.exception("agent_connector_redis_publish_failed", extra={"channel": channel})

    async def stream_text(self, req: AgentStreamRequest) -> AsyncIterator[dict[str, Any]]:
        channel = f"conversation:{req.tenant_id}:{req.session_id}"

        async with websockets.connect(
            self._agent_ws_url,
            ping_interval=20,
            ping_timeout=20,
        ) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "text",
                        "text": req.content,
                        "language": req.language or "auto",
                    }
                )
            )

            while True:
                raw = await ws.recv()
                try:
                    msg = json.loads(raw)
                except Exception:
                    logger.warning("agent_connector_non_json", extra={"raw": raw})
                    continue

                stage = msg.get("stage")

                if stage == "started":
                    event: dict[str, Any] = {
                        "type": "typing_start",
                        "tenant_id": req.tenant_id,
                        "session_id": req.session_id,
                        "message_id": req.message_id,
                    }
                    yield event
                    await self._maybe_publish(channel=channel, event=event)
                    continue

                # Any stage trace except "complete" becomes a non-final chunk.
                if stage and stage != "complete":
                    event = {
                        "type": "agent_chunk",
                        "tenant_id": req.tenant_id,
                        "session_id": req.session_id,
                        "message_id": req.message_id,
                        "content": f"[stage:{stage}]",
                        "is_final": False,
                    }
                    yield event
                    await self._maybe_publish(channel=channel, event=event)
                    continue

                if stage == "complete":
                    response_text = msg.get("response_text") or msg.get("response") or ""

                    chunk_event = {
                        "type": "agent_chunk",
                        "tenant_id": req.tenant_id,
                        "session_id": req.session_id,
                        "message_id": req.message_id,
                        "content": response_text,
                        "is_final": True,
                    }
                    yield chunk_event
                    await self._maybe_publish(channel=channel, event=chunk_event)

                    final_event = {
                        "type": "agent_final",
                        "tenant_id": req.tenant_id,
                        "session_id": req.session_id,
                        "message_id": req.message_id,
                        "content": response_text,
                    }
                    yield final_event
                    await self._maybe_publish(channel=channel, event=final_event)
                    return

                # Fallback: treat unknown messages as a chunk.
                if msg:
                    event = {
                        "type": "agent_chunk",
                        "tenant_id": req.tenant_id,
                        "session_id": req.session_id,
                        "message_id": req.message_id,
                        "content": json.dumps(msg, default=str),
                        "is_final": False,
                    }
                    yield event
                    await self._maybe_publish(channel=channel, event=event)


def build_default_connector(*, agent_ws_url: str) -> AgentConnector:
    return AgentConnector(agent_ws_url=agent_ws_url)

