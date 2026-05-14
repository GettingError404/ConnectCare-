from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import metrics as metrics_module
from app.core.config import settings
from app.core.logging import get_logger
from app.repositories.vector_embedding_async import DocumentEmbeddingAsyncRepository
from app.schemas.vector_embedding import (
    EmbedBatchRequest,
    EmbedBatchResponse,
    EmbedBatchResultItem,
    EmbedTextRequest,
    EmbedTextResponse,
    EmbeddedChunkResult,
    VectorDocumentCreate,
    VectorDocumentResponse,
)
from app.services.embeddings.cache import EmbeddingCache, build_embedding_cache
from app.services.embeddings.chunking import TokenSafeChunker
from app.services.embeddings.exceptions import PermanentEmbeddingError
from app.services.embeddings.provider_registry import EmbeddingProviderRegistry
from app.services.embeddings.retry import with_embedding_retry

logger = get_logger(__name__)


@dataclass
class _ResolvedProvider:
    provider_name: str
    model: str


class EmbeddingOrchestrationService:
    """Coordinates chunking, provider calls, caching and persistence."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        registry: EmbeddingProviderRegistry | None = None,
        cache: EmbeddingCache | None = None,
    ):
        self.db = db
        self.repo = DocumentEmbeddingAsyncRepository(db)
        self.registry = registry or EmbeddingProviderRegistry()
        self.cache = cache or build_embedding_cache()

    async def embed_text(self, *, tenant_id: UUID, request: EmbedTextRequest) -> EmbedTextResponse:
        started = time.perf_counter()
        provider = self._resolve_provider(request.provider, request.embedding_model)
        try:
            chunks = self._chunk_text(
                request.text,
                chunk_size_tokens=request.chunk_size_tokens,
                chunk_overlap_tokens=request.chunk_overlap_tokens,
            )
            if not chunks:
                raise PermanentEmbeddingError("text produced no chunks")

            persisted: list[EmbeddedChunkResult] = []
            for index, chunk_text in enumerate(chunks):
                vector = await self._get_or_generate_embedding(
                    provider_name=provider.provider_name,
                    model=provider.model,
                    text=chunk_text,
                )

                metadata = {
                    **(request.metadata or {}),
                    "chunk_index": index,
                    "chunk_count": len(chunks),
                    "provider": provider.provider_name,
                }
                payload = VectorDocumentCreate(
                    source_type=request.source_type,
                    source_id=request.source_id,
                    content=chunk_text,
                    embedding_model=provider.model,
                    embedding=vector,
                    metadata=metadata,
                )
                entity = await self.repo.create_document_embedding(tenant_id=tenant_id, payload=payload)
                persisted.append(
                    EmbeddedChunkResult(
                        chunk_index=index,
                        chunk_text=chunk_text,
                        token_estimate=TokenSafeChunker.estimate_tokens(chunk_text),
                        document=VectorDocumentResponse.model_validate(entity),
                    )
                )

            duration = time.perf_counter() - started
            metrics_module.observe_embedding_generation_latency(provider.provider_name, provider.model, duration)
            metrics_module.inc_embedding_requests(provider.provider_name, provider.model, "success")
            logger.info(
                "embed_text_success",
                extra={
                    "tenant_id": str(tenant_id),
                    "provider": provider.provider_name,
                    "model": provider.model,
                    "chunk_count": len(persisted),
                    "duration_seconds": round(duration, 4),
                },
            )

            return EmbedTextResponse(
                provider=provider.provider_name,
                embedding_model=provider.model,
                chunk_count=len(persisted),
                chunks=persisted,
                duration_seconds=duration,
            )
        except Exception:
            metrics_module.inc_embedding_requests(provider.provider_name, provider.model, "failure")
            raise

    async def embed_batch(self, *, tenant_id: UUID, request: EmbedBatchRequest) -> EmbedBatchResponse:
        started = time.perf_counter()
        items: list[EmbedBatchResultItem] = []
        succeeded = 0
        failed = 0

        for doc in request.items:
            text_request = EmbedTextRequest(
                source_type=doc.source_type,
                source_id=doc.source_id,
                text=doc.text,
                metadata=doc.metadata,
                provider=request.provider,
                embedding_model=request.embedding_model,
                chunk_size_tokens=request.chunk_size_tokens,
                chunk_overlap_tokens=request.chunk_overlap_tokens,
            )
            try:
                response = await self.embed_text(tenant_id=tenant_id, request=text_request)
                items.append(
                    EmbedBatchResultItem(
                        source_type=doc.source_type,
                        source_id=doc.source_id,
                        status="success",
                        chunk_count=response.chunk_count,
                        chunks=response.chunks,
                    )
                )
                succeeded += 1
            except Exception as exc:
                logger.exception(
                    "embed_batch_item_failed",
                    extra={
                        "tenant_id": str(tenant_id),
                        "source_type": doc.source_type,
                        "source_id": str(doc.source_id),
                        "error": str(exc),
                    },
                )
                metrics_module.inc_embedding_requests(request.provider or settings.EMBEDDING_PROVIDER, request.embedding_model or settings.EMBEDDING_MODEL, "failure")
                items.append(
                    EmbedBatchResultItem(
                        source_type=doc.source_type,
                        source_id=doc.source_id,
                        status="failed",
                        chunk_count=0,
                        error=str(exc),
                        chunks=[],
                    )
                )
                failed += 1

        duration = time.perf_counter() - started
        return EmbedBatchResponse(
            provider=request.provider or settings.EMBEDDING_PROVIDER,
            embedding_model=request.embedding_model or settings.EMBEDDING_MODEL,
            total=len(request.items),
            succeeded=succeeded,
            failed=failed,
            duration_seconds=duration,
            items=items,
        )

    def _resolve_provider(self, provider_name: str | None, model: str | None) -> _ResolvedProvider:
        provider = self.registry.create(provider_name=provider_name, model=model)
        return _ResolvedProvider(provider_name=provider.name, model=provider.model)

    def _chunk_text(self, text: str, chunk_size_tokens: int | None = None, chunk_overlap_tokens: int | None = None) -> list[str]:
        cleaned = text.strip()
        if not cleaned:
            raise PermanentEmbeddingError("text must not be empty")
        if len(cleaned) > settings.EMBEDDING_MAX_TEXT_LENGTH:
            raise PermanentEmbeddingError(
                f"text exceeds EMBEDDING_MAX_TEXT_LENGTH={settings.EMBEDDING_MAX_TEXT_LENGTH}"
            )

        chunker = TokenSafeChunker(
            chunk_size_tokens=chunk_size_tokens,
            overlap_tokens=chunk_overlap_tokens,
        )
        return chunker.chunk_text(cleaned)

    async def _get_or_generate_embedding(self, *, provider_name: str, model: str, text: str) -> list[float]:
        cache_key = self._cache_key(provider_name=provider_name, model=model, text=text)
        cached = await self.cache.get(cache_key)
        if cached is not None:
            metrics_module.inc_embedding_cache_hits(provider_name, model)
            return cached

        provider = self.registry.create(provider_name=provider_name, model=model)

        try:
            vector = await with_embedding_retry(lambda: provider.generate_embedding(text))
        except Exception as exc:
            metrics_module.inc_embedding_provider_failures(provider_name, model)
            logger.exception(
                "embedding_provider_failed",
                extra={
                    "provider": provider_name,
                    "model": model,
                    "error": str(exc),
                },
            )
            raise

        await self.cache.set(cache_key, vector, settings.EMBEDDING_CACHE_TTL_SECONDS)
        return vector

    @staticmethod
    def _cache_key(*, provider_name: str, model: str, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{settings.EMBEDDING_CACHE_PREFIX}:{provider_name}:{model}:{digest}"
