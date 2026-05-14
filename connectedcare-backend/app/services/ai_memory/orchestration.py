from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import metrics as metrics_module
from app.core.config import settings
from app.core.logging import get_logger
from app.repositories.ai_memory_intelligence_async import AIMemoryIntelligenceRepository
from app.schemas.ai_memory import (
    ConversationMemoryIngestRequest,
    DeleteMemoryRequest,
    DocumentMemoryIngestRequest,
    MemoryAnalyticsResponse,
    MemoryIngestResponse,
    MemoryRetrieveRequest,
    MemoryRetrieveResponse,
    RetrievedMemoryItem,
)
from app.schemas.ai_memory import (
    ClinicalNoteMemoryIngestRequest,
    GenerateContextRequest,
    GenerateContextResponse,
    IngestedMemoryChunk,
    MemorySummaryResponse,
    SummarizeMemoryRequest,
)
from app.services.ai_memory.cache import RetrievalCache, build_retrieval_cache
from app.services.ai_memory.context_builder import AIMemoryContextBuilder
from app.services.ai_memory.retrieval_engine import AIMemoryRetrievalEngine
from app.services.ai_memory.summarization_service import AIMemorySummarizationService
from app.services.embeddings.cache import EmbeddingCache, build_embedding_cache
from app.services.embeddings.chunking import TokenSafeChunker
from app.services.embeddings.provider_registry import EmbeddingProviderRegistry
from app.services.embeddings.retry import with_embedding_retry

logger = get_logger(__name__)


class AIMemoryOrchestrationService:
    """Main AI memory intelligence orchestration service."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        embedding_cache: EmbeddingCache | None = None,
        retrieval_cache: RetrievalCache | None = None,
    ):
        self.db = db
        self.repo = AIMemoryIntelligenceRepository(db)
        self.provider_registry = EmbeddingProviderRegistry()
        self.embedding_cache = embedding_cache or build_embedding_cache()
        self.retrieval_cache = retrieval_cache or build_retrieval_cache()
        self.chunker = TokenSafeChunker()
        self.retrieval_engine = AIMemoryRetrievalEngine(self.repo)
        self.summarization_service = AIMemorySummarizationService(self.repo)
        self.context_builder = AIMemoryContextBuilder(self.repo)

    async def ingest_conversation_memory(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID | None,
        payload: ConversationMemoryIngestRequest,
    ) -> MemoryIngestResponse:
        return await self._ingest(
            tenant_id=tenant_id,
            user_id=user_id,
            payload_content=payload.content,
            memory_type="short_term",
            source_type="conversation",
            source_id=payload.conversation_id,
            title=payload.title,
            tags=payload.tags,
            metadata={**(payload.metadata or {}), "conversation_id": str(payload.conversation_id)},
            retention_days=payload.retention_days or settings.AI_MEMORY_RETENTION_SHORT_DAYS,
        )

    async def ingest_document_memory(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID | None,
        payload: DocumentMemoryIngestRequest,
    ) -> MemoryIngestResponse:
        return await self._ingest(
            tenant_id=tenant_id,
            user_id=user_id,
            payload_content=payload.content,
            memory_type="long_term",
            source_type="document",
            source_id=payload.document_id,
            title=payload.title,
            tags=payload.tags,
            metadata={**(payload.metadata or {}), "document_id": str(payload.document_id)},
            retention_days=payload.retention_days or settings.AI_MEMORY_RETENTION_LONG_DAYS,
        )

    async def ingest_clinical_note_memory(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID | None,
        payload: ClinicalNoteMemoryIngestRequest,
    ) -> MemoryIngestResponse:
        note_source_id = payload.note_id or payload.source_id
        meta = payload.metadata or {}
        if payload.patient_id:
            meta["patient_id"] = str(payload.patient_id)
        if payload.note_id:
            meta["note_id"] = str(payload.note_id)
        return await self._ingest(
            tenant_id=tenant_id,
            user_id=user_id,
            payload_content=payload.content,
            memory_type="episodic",
            source_type="clinical_note",
            source_id=note_source_id,
            title=payload.title,
            tags=payload.tags,
            metadata=meta,
            retention_days=payload.retention_days or settings.AI_MEMORY_RETENTION_EPISODIC_DAYS,
        )

    async def retrieve_memories(self, *, tenant_id: UUID, payload: MemoryRetrieveRequest) -> MemoryRetrieveResponse:
        retrieval_key = self._retrieval_cache_key(tenant_id=tenant_id, payload=payload)
        cached = await self.retrieval_cache.get(retrieval_key)
        if cached:
            logger.info("ai_memory_retrieval_cache_hit", extra={"tenant_id": str(tenant_id), "top_k": payload.top_k})
            return MemoryRetrieveResponse.model_validate(cached)

        query_embedding = await self._generate_embedding(payload.query)
        ranked, mode = await self.retrieval_engine.retrieve(
            tenant_id=tenant_id,
            query_text=payload.query,
            query_embedding=query_embedding,
            top_k=payload.top_k,
            memory_types=payload.memory_types,
            source_types=payload.source_types,
            metadata_filter=payload.metadata_filter,
            conversation_id=payload.conversation_id,
            use_hybrid_search=payload.use_hybrid_search,
            recency_boost_weight=payload.recency_boost_weight,
        )

        response = MemoryRetrieveResponse(
            retrieval_mode=mode,
            total_results=len(ranked),
            results=[
                RetrievedMemoryItem(
                    memory_id=item.candidate.memory_id,
                    chunk_id=item.candidate.chunk_id,
                    content=item.candidate.chunk_text,
                    memory_type=item.candidate.memory_type,
                    source_type=item.candidate.source_type,
                    semantic_score=item.candidate.semantic_score,
                    hybrid_score=item.hybrid_score,
                    recency_score=item.recency_score,
                    final_score=item.final_score,
                    created_at=item.candidate.created_at,
                    metadata=item.candidate.metadata,
                )
                for item in ranked
            ],
        )
        await self.retrieval_cache.set(
            retrieval_key,
            response.model_dump(mode="json"),
            ttl_seconds=settings.AI_MEMORY_RETRIEVAL_CACHE_TTL_SECONDS,
        )
        logger.info(
            "ai_memory_retrieval_completed",
            extra={
                "tenant_id": str(tenant_id),
                "mode": mode,
                "results": response.total_results,
            },
        )
        return response

    async def generate_context(self, *, tenant_id: UUID, payload: GenerateContextRequest) -> GenerateContextResponse:
        retrieval_response = await self.retrieve_memories(
            tenant_id=tenant_id,
            payload=MemoryRetrieveRequest(
                query=payload.user_query,
                top_k=payload.top_k,
                conversation_id=payload.conversation_id,
                use_hybrid_search=True,
            ),
        )

        from app.services.ai_memory.ranking_engine import RankedCandidate
        from app.repositories.ai_memory_intelligence_async import RetrievalCandidate

        ranked_candidates = [
            RankedCandidate(
                candidate=RetrievalCandidate(
                    memory_id=i.memory_id,
                    chunk_id=i.chunk_id,
                    chunk_text=i.content,
                    memory_type=i.memory_type,
                    source_type=i.source_type,
                    created_at=i.created_at,
                    semantic_score=i.semantic_score,
                    metadata=i.metadata,
                ),
                hybrid_score=i.hybrid_score,
                recency_score=i.recency_score,
                final_score=i.final_score,
            )
            for i in retrieval_response.results
        ]

        context, memory_ids = await self.context_builder.build_and_persist_context(
            tenant_id=tenant_id,
            conversation_id=payload.conversation_id,
            user_query=payload.user_query,
            ranked_results=ranked_candidates,
            token_budget=payload.token_budget,
        )
        await self.db.commit()
        logger.info(
            "ai_memory_context_built",
            extra={
                "tenant_id": str(tenant_id),
                "conversation_id": str(payload.conversation_id),
                "memory_count": len(memory_ids),
            },
        )
        return GenerateContextResponse(
            context_id=context.id,
            context_text=context.context_text,
            tokens_used=context.tokens_used,
            token_budget=context.token_budget,
            memory_ids=memory_ids,
        )

    async def summarize_memory(self, *, tenant_id: UUID, payload: SummarizeMemoryRequest) -> MemorySummaryResponse | None:
        summary = await self.summarization_service.summarize_memory(
            tenant_id=tenant_id,
            memory_id=payload.memory_id,
            max_summary_tokens=payload.max_summary_tokens,
        )
        if summary is None:
            return None
        await self.db.commit()
        return MemorySummaryResponse(
            summary_id=summary.id,
            memory_id=summary.memory_id,
            summary_text=summary.summary_text,
            token_count=summary.token_count,
        )

    async def delete_memory(self, *, tenant_id: UUID, payload: DeleteMemoryRequest) -> bool:
        if payload.hard_delete:
            deleted = await self.repo.hard_delete_memory(tenant_id=tenant_id, memory_id=payload.memory_id)
        else:
            deleted = await self.repo.soft_delete_memory(tenant_id=tenant_id, memory_id=payload.memory_id)
        await self.db.commit()
        return deleted

    async def analytics(self, *, tenant_id: UUID) -> MemoryAnalyticsResponse:
        data = await self.repo.analytics(tenant_id=tenant_id)
        return MemoryAnalyticsResponse(**data)

    async def apply_decay_and_retention(self, *, tenant_id: UUID) -> int:
        """Applies memory decay and soft-deletes expired rows."""
        # Minimal implementation in service layer for Celery scheduling.
        now = datetime.now(timezone.utc)
        stmt = (
            "UPDATE ai_memories "
            "SET recency_score = GREATEST(0.0, recency_score - decay_rate), "
            "deleted_at = CASE WHEN expires_at IS NOT NULL AND expires_at <= :now THEN :now ELSE deleted_at END "
            "WHERE tenant_id = :tenant_id AND deleted_at IS NULL"
        )
        result = await self.db.execute(text(stmt), {"tenant_id": str(tenant_id), "now": now})
        await self.db.commit()
        return int(result.rowcount or 0)

    async def _ingest(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID | None,
        payload_content: str,
        memory_type: str,
        source_type: str,
        source_id: UUID | None,
        title: str | None,
        tags: list[str],
        metadata: dict | None,
        retention_days: int,
    ) -> MemoryIngestResponse:
        cleaned = payload_content.strip()
        if not cleaned:
            raise ValueError("content cannot be empty")

        token_count = len(cleaned.split())
        try:
            memory = await self.repo.create_memory(
                tenant_id=tenant_id,
                user_id=user_id,
                memory_type=memory_type,
                source_type=source_type,
                source_id=source_id,
                title=title,
                content=cleaned,
                token_count=token_count,
                tags=tags,
                metadata=metadata,
                retention_days=retention_days,
                decay_rate=settings.AI_MEMORY_DECAY_RATE,
            )

            chunks = self.chunker.chunk_text(cleaned)
            chunk_models = []
            provider = self.provider_registry.create(provider_name=None, model=settings.EMBEDDING_MODEL)
            for idx, chunk_text in enumerate(chunks):
                embedding = await self._generate_embedding(chunk_text)
                chunk = await self.repo.create_chunk(
                    tenant_id=tenant_id,
                    memory_id=memory.id,
                    chunk_index=idx,
                    chunk_text=chunk_text,
                    token_count=len(chunk_text.split()),
                    embedding=embedding,
                    embedding_model=provider.model,
                    metadata={**(metadata or {}), "chunk_index": idx},
                )
                chunk_models.append(chunk)

            await self.db.commit()
            metrics_module.inc_ai_memory_ingestions(source_type=source_type, status="success")
            logger.info(
                "ai_memory_ingest_success",
                extra={
                    "tenant_id": str(tenant_id),
                    "source_type": source_type,
                    "memory_type": memory_type,
                    "chunk_count": len(chunk_models),
                },
            )
            return MemoryIngestResponse(
                memory_id=memory.id,
                chunk_count=len(chunk_models),
                chunks=[
                    IngestedMemoryChunk(
                        id=c.id,
                        chunk_index=c.chunk_index,
                        token_count=c.token_count,
                    )
                    for c in chunk_models
                ],
            )
        except Exception:
            metrics_module.inc_ai_memory_ingestions(source_type=source_type, status="failure")
            logger.exception(
                "ai_memory_ingest_failed",
                extra={
                    "tenant_id": str(tenant_id),
                    "source_type": source_type,
                    "memory_type": memory_type,
                },
            )
            raise

    async def _generate_embedding(self, text: str) -> list[float]:
        provider = self.provider_registry.create(provider_name=None, model=settings.EMBEDDING_MODEL)
        cache_key = self._embedding_cache_key(provider=provider.name, model=provider.model, text=text)
        cached = await self.embedding_cache.get(cache_key)
        if cached is not None:
            return cached

        vector = await with_embedding_retry(lambda: provider.generate_embedding(text))
        await self.embedding_cache.set(cache_key, vector, settings.EMBEDDING_CACHE_TTL_SECONDS)
        return vector

    @staticmethod
    def _embedding_cache_key(*, provider: str, model: str, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{settings.EMBEDDING_CACHE_PREFIX}:aimemory:{provider}:{model}:{digest}"

    @staticmethod
    def _retrieval_cache_key(*, tenant_id: UUID, payload: MemoryRetrieveRequest) -> str:
        stable = json.dumps(payload.model_dump(mode="json"), sort_keys=True)
        digest = hashlib.sha256(stable.encode("utf-8")).hexdigest()
        return f"{settings.AI_MEMORY_RETRIEVAL_CACHE_PREFIX}:{tenant_id}:{digest}"
