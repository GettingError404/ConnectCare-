from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.embeddings.exceptions import PermanentEmbeddingError, TransientEmbeddingError
from app.services.embeddings.interfaces import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama local embeddings provider over HTTP API."""

    def __init__(self, model: str, dimension: int):
        self.name = "ollama"
        self.model = model
        self.dimension = dimension

    async def generate_embedding(self, text: str) -> list[float]:
        payload = {
            "model": self.model,
            "prompt": text,
        }

        timeout = httpx.Timeout(settings.EMBEDDING_PROVIDER_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings",
                    json=payload,
                )
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                raise TransientEmbeddingError(f"Ollama connection error: {exc}") from exc

        if response.status_code in {408, 409, 425, 429} or 500 <= response.status_code <= 599:
            raise TransientEmbeddingError(
                f"Ollama transient failure status={response.status_code} body={response.text[:300]}"
            )
        if response.status_code >= 400:
            raise PermanentEmbeddingError(
                f"Ollama permanent failure status={response.status_code} body={response.text[:300]}"
            )

        data = response.json()
        vector = data.get("embedding")
        if not isinstance(vector, list):
            raise PermanentEmbeddingError("Invalid Ollama embedding response shape")

        if len(vector) != self.dimension:
            raise PermanentEmbeddingError(
                f"Ollama embedding dimension mismatch expected={self.dimension} actual={len(vector)}"
            )
        return [float(x) for x in vector]
