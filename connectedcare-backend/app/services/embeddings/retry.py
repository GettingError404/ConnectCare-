from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable

from app.core.config import settings
from app.services.embeddings.exceptions import EmbeddingTimeoutError, PermanentEmbeddingError, TransientEmbeddingError


async def with_embedding_retry(
    operation: Callable[[], Awaitable[list[float]]],
    *,
    timeout_seconds: float | None = None,
    max_retries: int | None = None,
    backoff_base_seconds: float | None = None,
) -> list[float]:
    """Run embedding operation with timeout and exponential-backoff retries."""
    retries = max_retries if max_retries is not None else settings.EMBEDDING_MAX_RETRIES
    timeout = timeout_seconds if timeout_seconds is not None else settings.EMBEDDING_PROVIDER_TIMEOUT_SECONDS
    backoff_base = backoff_base_seconds if backoff_base_seconds is not None else settings.EMBEDDING_RETRY_BACKOFF_SECONDS

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await asyncio.wait_for(operation(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            last_error = EmbeddingTimeoutError(f"Embedding timeout after {timeout}s")
        except PermanentEmbeddingError:
            raise
        except TransientEmbeddingError as exc:
            last_error = exc
        except Exception as exc:
            # Unknown failures are treated as transient to maximize resilience.
            last_error = TransientEmbeddingError(str(exc))

        if attempt >= retries:
            break

        delay = (backoff_base * (2 ** attempt)) + random.uniform(0.0, backoff_base)
        await asyncio.sleep(delay)

    assert last_error is not None
    if isinstance(last_error, PermanentEmbeddingError):
        raise last_error
    raise TransientEmbeddingError(str(last_error))
