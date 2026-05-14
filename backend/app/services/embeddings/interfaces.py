from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Provider contract for embedding generation."""

    name: str
    model: str
    dimension: int

    @abstractmethod
    async def generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text input."""
        raise NotImplementedError
