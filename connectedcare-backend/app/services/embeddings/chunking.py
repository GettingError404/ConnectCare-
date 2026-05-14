from __future__ import annotations

import re

from app.core.config import settings

_TOKEN_RE = re.compile(r"\S+")


class TokenSafeChunker:
    """Token-approximate chunker with overlap for embedding pipelines."""

    def __init__(self, chunk_size_tokens: int | None = None, overlap_tokens: int | None = None):
        self.chunk_size_tokens = chunk_size_tokens or settings.EMBEDDING_CHUNK_SIZE_TOKENS
        self.overlap_tokens = overlap_tokens if overlap_tokens is not None else settings.EMBEDDING_CHUNK_OVERLAP_TOKENS
        if self.overlap_tokens >= self.chunk_size_tokens:
            raise ValueError("overlap_tokens must be smaller than chunk_size_tokens")

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return len(_TOKEN_RE.findall(text))

    def chunk_text(self, text: str) -> list[str]:
        tokens = _TOKEN_RE.findall(text)
        if not tokens:
            return []

        if len(tokens) <= self.chunk_size_tokens:
            return [" ".join(tokens)]

        chunks: list[str] = []
        start = 0
        step = self.chunk_size_tokens - self.overlap_tokens
        while start < len(tokens):
            end = min(start + self.chunk_size_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(" ".join(chunk_tokens))
            if end == len(tokens):
                break
            start += step
        return chunks
