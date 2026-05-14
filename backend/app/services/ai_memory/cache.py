from __future__ import annotations

import json
from abc import ABC, abstractmethod

from redis.asyncio import Redis

from app.core.config import settings


class RetrievalCache(ABC):
    @abstractmethod
    async def get(self, key: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        raise NotImplementedError


class NullRetrievalCache(RetrievalCache):
    async def get(self, key: str) -> dict | None:
        return None

    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        return None


class RedisRetrievalCache(RetrievalCache):
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> dict | None:
        payload = await self.redis.get(key)
        if not payload:
            return None
        return json.loads(payload)

    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        await self.redis.set(key, json.dumps(value), ex=ttl_seconds)


def build_retrieval_cache() -> RetrievalCache:
    if not settings.REDIS_URL:
        return NullRetrievalCache()
    return RedisRetrievalCache(settings.REDIS_URL)
