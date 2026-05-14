from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.embeddings.exceptions import PermanentEmbeddingError, TransientEmbeddingError
from app.services.embeddings.interfaces import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings provider over HTTP API."""

    def __init__(self, model: str, dimension: int):
        self.name = "openai"
        self.model = model
        self.dimension = dimension

    async def generate_embedding(self, text: str) -> list[float]:
        if not settings.OPENAI_API_KEY:
            raise PermanentEmbeddingError("OPENAI_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": text,
            "model": self.model,
        }

        timeout = httpx.Timeout(settings.EMBEDDING_PROVIDER_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    f"{settings.OPENAI_BASE_URL.rstrip('/')}/embeddings",
                    headers=headers,
                    json=payload,
                )
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                raise TransientEmbeddingError(f"OpenAI connection error: {exc}") from exc

        if response.status_code in {408, 409, 425, 429} or 500 <= response.status_code <= 599:
            raise TransientEmbeddingError(
                f"OpenAI transient failure status={response.status_code} body={response.text[:300]}"
            )
        if response.status_code >= 400:
            raise PermanentEmbeddingError(
                f"OpenAI permanent failure status={response.status_code} body={response.text[:300]}"
            )

        data = response.json()
        try:
            vector = data["data"][0]["embedding"]
        except Exception as exc:
            raise PermanentEmbeddingError("Invalid OpenAI embedding response shape") from exc

        if len(vector) != self.dimension:
            raise PermanentEmbeddingError(
                f"OpenAI embedding dimension mismatch expected={self.dimension} actual={len(vector)}"
            )
        return [float(x) for x in vector]
