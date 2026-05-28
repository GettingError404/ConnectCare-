from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Sequence
from uuid import UUID

try:
    import redis.asyncio as redis_asyncio
except Exception:  # pragma: no cover
    redis_asyncio = None

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubscriptionSpec:
    channel: str


class RedisPubSub:
    """Async Redis Pub/Sub helper for websocket fanout.

    - Uses redis.asyncio for non-blocking pub/sub
    - Provides per-gateway session subscribe loop via `subscribe_forever`
    - Exposes shutdown via cancelable task

    Channel naming convention (recommended):
      - alerts:{tenant_id}
      - conversation:{tenant_id}:{session_id}
      - agent:{tenant_id}:{session_id}
      - voice:{tenant_id}:{session_id} (future)
    """

    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[Any] = None
        self._lock = asyncio.Lock()

    async def _ensure_client(self) -> Any:
        if not self._redis_url:
            raise RuntimeError("REDIS_URL not configured")
        if redis_asyncio is None:
            raise RuntimeError("redis.asyncio not available")

        async with self._lock:
            if self._redis is None:
                self._redis = redis_asyncio.from_url(self._redis_url, decode_responses=True)
            return self._redis

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        payload = json.dumps(event, default=str)
        try:
            r = await self._ensure_client()
            await r.publish(channel, payload)
        except Exception:
            logger.exception("redis_pubsub_publish_failed", extra={"channel": channel})

    async def subscribe_forever(
        self,
        *,
        channels: Sequence[str],
        on_message: Callable[[dict[str, Any]], Awaitable[None]],
        stop_event: Optional[asyncio.Event] = None,
    ) -> None:
        """Subscribe to `channels` and call `on_message` for each parsed JSON message."""

        if not channels:
            return

        r = await self._ensure_client()
        pubsub = r.pubsub(ignore_subscribe_messages=True)
        try:
            await pubsub.subscribe(*channels)
            logger.info("redis_pubsub_subscribed", extra={"channels": list(channels)})

            while True:
                if stop_event is not None and stop_event.is_set():
                    return

                # Use timeout so we can react to stop_event
                msg = await pubsub.get_message(timeout=1.0)
                if msg is None:
                    await asyncio.sleep(0)  # yield
                    continue

                if msg.get("type") != "message":
                    continue

                raw = msg.get("data")
                try:
                    event = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    logger.warning("redis_pubsub_bad_json", extra={"raw": raw})
                    continue

                await on_message(event)
        finally:
            try:
                await pubsub.unsubscribe(*channels)
            except Exception:
                pass
            try:
                await pubsub.close()
            except Exception:
                pass

    async def close(self) -> None:
        async with self._lock:
            if self._redis is not None:
                try:
                    await self._redis.close()
                except Exception:
                    pass
                self._redis = None


def conversation_channel(tenant_id: UUID, session_id: UUID) -> str:
    return f"conversation:{tenant_id}:{session_id}"


def agent_channel(tenant_id: UUID, session_id: UUID) -> str:
    return f"agent:{tenant_id}:{session_id}"


def alerts_channel(tenant_id: UUID) -> str:
    return f"alerts:{tenant_id}"

