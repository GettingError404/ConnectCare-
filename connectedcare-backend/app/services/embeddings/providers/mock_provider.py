from __future__ import annotations

import hashlib

from app.core.config import settings
from app.services.embeddings.interfaces import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic local provider for tests and offline development."""

    def __init__(self, model: str):
        self.name = "mock"
        self.model = model
        self.dimension = settings.PGVECTOR_EMBEDDING_DIMENSION

    async def generate_embedding(self, text: str) -> list[float]:
        # Deterministic pseudo-embedding from SHA256 digest expansion.
        seed = hashlib.sha256(f"{self.model}:{text}".encode("utf-8")).digest()
        vector: list[float] = []
        material = seed
        while len(vector) < self.dimension:
            material = hashlib.sha256(material).digest()
            for i in range(0, len(material), 4):
                if len(vector) >= self.dimension:
                    break
                chunk = material[i : i + 4]
                if len(chunk) < 4:
                    break
                raw = int.from_bytes(chunk, "big", signed=False)
                vector.append((raw / 2147483647.5) - 1.0)
        return vector
