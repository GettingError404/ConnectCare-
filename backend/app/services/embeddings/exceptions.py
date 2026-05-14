from __future__ import annotations


class EmbeddingError(Exception):
    """Base exception for embedding orchestration."""


class TransientEmbeddingError(EmbeddingError):
    """Recoverable embedding provider error."""


class PermanentEmbeddingError(EmbeddingError):
    """Non-recoverable embedding provider error."""


class EmbeddingTimeoutError(TransientEmbeddingError):
    """Provider timed out while generating embedding."""
