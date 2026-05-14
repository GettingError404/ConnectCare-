from __future__ import annotations

from collections.abc import Callable

from app.core.config import settings
from app.services.embeddings.exceptions import PermanentEmbeddingError
from app.services.embeddings.interfaces import EmbeddingProvider
from app.services.embeddings.providers.mock_provider import MockEmbeddingProvider
from app.services.embeddings.providers.ollama_provider import OllamaEmbeddingProvider
from app.services.embeddings.providers.openai_provider import OpenAIEmbeddingProvider


MODEL_PROVIDER_DEFAULTS: dict[str, str] = {
    "text-embedding-3-small": "openai",
    "nomic-embed-text": "ollama",
}


MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "nomic-embed-text": 768,
}


ProviderBuilder = Callable[[str, int], EmbeddingProvider]


class EmbeddingProviderRegistry:
    """Provider factory and registry for embedding providers."""

    def __init__(self):
        self._builders: dict[str, ProviderBuilder] = {
            "openai": lambda model, dimension: OpenAIEmbeddingProvider(model=model, dimension=dimension),
            "ollama": lambda model, dimension: OllamaEmbeddingProvider(model=model, dimension=dimension),
            "mock": lambda model, dimension: MockEmbeddingProvider(model=model),
        }

    def register(self, provider_name: str, builder: ProviderBuilder) -> None:
        self._builders[provider_name] = builder

    def resolve_dimension(self, model: str) -> int:
        configured = settings.PGVECTOR_EMBEDDING_DIMENSION
        known = MODEL_DIMENSIONS.get(model)
        if known is not None and known != configured:
            raise PermanentEmbeddingError(
                f"Configured PGVECTOR_EMBEDDING_DIMENSION={configured} does not match model {model} dimension {known}"
            )
        return configured

    def create(self, provider_name: str | None = None, model: str | None = None) -> EmbeddingProvider:
        model_name = model or settings.EMBEDDING_MODEL
        chosen_provider = provider_name or MODEL_PROVIDER_DEFAULTS.get(model_name) or settings.EMBEDDING_PROVIDER
        if chosen_provider not in self._builders:
            raise PermanentEmbeddingError(f"Unsupported embedding provider: {chosen_provider}")

        dimension = self.resolve_dimension(model_name)
        return self._builders[chosen_provider](model_name, dimension)
