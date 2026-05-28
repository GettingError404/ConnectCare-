from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional
from uuid import UUID

try:
    import redis.asyncio as redis_async
except Exception:  # pragma: no cover
    redis_async = None

from app.core.config import settings
logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class RedisChannel:
    name: str


class RedisPubSub:
    def __init__(self):
        self._redis = None
        if redis_async is None:
            return
        if not settings.REDIS_URL:
            return
        try:
            self._redis = redis_async.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            logger.exception("failed_init_redis_pubsub")
            self._redis = None

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        if not self._redis:
            logger.warning("redis_publish_no_client", extra={"channel": channel})
            return
        payload = json.dumps(event, default=str)
        await self._redis.publish(channel, payload)

    async def subscribe(self, *channels: str) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        if not self._redis:
            # yield nothing
            while False:
                yield "", {}
            return

        pubsub = self._redis.pubsub()
        await pubsub.subscribe(*channels)
        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not msg:
                    continue
                if msg.get("type") != "message":
                    continue
                ch = str(msg.get("channel"))
                raw = msg.get("data")
                try:
                    data = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode("utf-8"))
                except Exception:
                    data = {"raw": raw}
                yield ch, data
        finally:
            try:
                await pubsub.unsubscribe(*channels)
            except Exception:
                pass
            try:
                await pubsub.close()
            except Exception:
                pass


def channel_alerts(tenant_id: UUID) -> str:
    return f"alerts:{tenant_id}"


def channel_conversation(tenant_id: UUID, session_id: UUID) -> str:
    return f"conversation:{tenant_id}:{session_id}"


def channel_agent(tenant_id: UUID, session_id: UUID) -> str:
    return f"agent:{tenant_id}:{session_id}"


redis_bus = RedisPubSub()

