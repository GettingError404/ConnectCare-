from __future__ import annotations

import json
from abc import ABC, abstractmethod

from redis.asyncio import Redis

from app.core.config import settings


class EmbeddingCache(ABC):
    @abstractmethod
    async def get(self, key: str) -> list[float] | None:
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: list[float], ttl_seconds: int) -> None:
        raise NotImplementedError


class NullEmbeddingCache(EmbeddingCache):
    async def get(self, key: str) -> list[float] | None:
        return None

    async def set(self, key: str, value: list[float], ttl_seconds: int) -> None:
        return None


class RedisEmbeddingCache(EmbeddingCache):
    """Redis-backed cache for embedding vectors."""

    def __init__(self, redis_url: str):
        self._redis = Redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> list[float] | None:
        payload = await self._redis.get(key)
        if not payload:
            return None
        parsed = json.loads(payload)
        if not isinstance(parsed, list):
            return None
        return [float(x) for x in parsed]

    async def set(self, key: str, value: list[float], ttl_seconds: int) -> None:
        await self._redis.set(key, json.dumps(value), ex=ttl_seconds)


def build_embedding_cache() -> EmbeddingCache:
    if not settings.REDIS_URL:
        return NullEmbeddingCache()
    return RedisEmbeddingCache(settings.REDIS_URL)
