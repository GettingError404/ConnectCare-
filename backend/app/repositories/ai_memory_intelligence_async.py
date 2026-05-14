from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import String, and_, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_memory_intelligence import (
    AIMemory,
    ConversationContext,
    MemoryChunk,
    MemoryRetrievalLog,
    MemorySummary,
)


@dataclass
class RetrievalCandidate:
    memory_id: UUID
    chunk_id: UUID
    chunk_text: str
    memory_type: str
    source_type: str
    created_at: datetime
    semantic_score: float
    metadata: dict[str, Any] | None


class AIMemoryIntelligenceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_memory(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID | None,
        memory_type: str,
        source_type: str,
        source_id: UUID | None,
        title: str | None,
        content: str,
        token_count: int,
        tags: list[str] | None,
        metadata: dict | None,
        retention_days: int,
        decay_rate: float,
    ) -> AIMemory:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)

        existing_stmt = select(AIMemory).where(
            AIMemory.tenant_id == tenant_id,
            AIMemory.content_hash == content_hash,
            AIMemory.deleted_at.is_(None),
        )
        existing = (await self.session.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        entity = AIMemory(
            tenant_id=tenant_id,
            user_id=user_id,
            memory_type=memory_type,
            source_type=source_type,
            source_id=source_id,
            title=title,
            content=content,
            content_hash=content_hash,
            token_count=token_count,
            tags=tags,
            metadata_json=metadata,
            retention_days=retention_days,
            decay_rate=decay_rate,
            expires_at=expires_at,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def create_chunk(
        self,
        *,
        tenant_id: UUID,
        memory_id: UUID,
        chunk_index: int,
        chunk_text: str,
        token_count: int,
        embedding: list[float],
        embedding_model: str,
        metadata: dict | None,
    ) -> MemoryChunk:
        chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
        entity = MemoryChunk(
            tenant_id=tenant_id,
            memory_id=memory_id,
            chunk_index=chunk_index,
            chunk_text=chunk_text,
            chunk_hash=chunk_hash,
            token_count=token_count,
            embedding_model=embedding_model,
            embedding_dimension=len(embedding),
            embedding=embedding,
            metadata_json=metadata,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def semantic_search(
        self,
        *,
        tenant_id: UUID,
        query_embedding: list[float],
        top_k: int,
        memory_types: list[str] | None = None,
        source_types: list[str] | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[RetrievalCandidate]:
        distance_expr = MemoryChunk.embedding.cosine_distance(query_embedding)

        stmt = (
            select(
                AIMemory.id.label("memory_id"),
                MemoryChunk.id.label("chunk_id"),
                MemoryChunk.chunk_text,
                AIMemory.memory_type,
                AIMemory.source_type,
                AIMemory.created_at,
                (1.0 - distance_expr).label("semantic_score"),
                AIMemory.metadata_json,
            )
            .join(MemoryChunk, MemoryChunk.memory_id == AIMemory.id)
            .where(
                AIMemory.tenant_id == tenant_id,
                MemoryChunk.tenant_id == tenant_id,
                AIMemory.deleted_at.is_(None),
                MemoryChunk.deleted_at.is_(None),
                or_(AIMemory.expires_at.is_(None), AIMemory.expires_at > datetime.now(timezone.utc)),
            )
            .order_by(distance_expr)
            .limit(top_k)
        )

        if memory_types:
            stmt = stmt.where(AIMemory.memory_type.in_(memory_types))
        if source_types:
            stmt = stmt.where(AIMemory.source_type.in_(source_types))
        if metadata_filter:
            for key, value in metadata_filter.items():
                stmt = stmt.where(AIMemory.metadata_json[key].astext == str(value))

        rows = (await self.session.execute(stmt)).all()
        return [
            RetrievalCandidate(
                memory_id=row.memory_id,
                chunk_id=row.chunk_id,
                chunk_text=row.chunk_text,
                memory_type=row.memory_type,
                source_type=row.source_type,
                created_at=row.created_at,
                semantic_score=float(row.semantic_score),
                metadata=row.metadata_json,
            )
            for row in rows
        ]

    async def hybrid_keyword_search(
        self,
        *,
        tenant_id: UUID,
        query: str,
        top_k: int,
    ) -> dict[UUID, float]:
        stmt = (
            select(
                MemoryChunk.id,
                func.similarity(MemoryChunk.chunk_text, query).label("score"),
            )
            .where(
                MemoryChunk.tenant_id == tenant_id,
                MemoryChunk.deleted_at.is_(None),
                MemoryChunk.chunk_text.ilike(f"%{query}%"),
            )
            .order_by(desc("score"))
            .limit(top_k)
        )

        try:
            rows = (await self.session.execute(stmt)).all()
        except Exception:
            # similarity() may be unavailable if pg_trgm extension is not enabled.
            fallback_stmt = (
                select(MemoryChunk.id)
                .where(
                    MemoryChunk.tenant_id == tenant_id,
                    MemoryChunk.deleted_at.is_(None),
                    MemoryChunk.chunk_text.ilike(f"%{query}%"),
                )
                .limit(top_k)
            )
            rows = [(row.id, 0.2) for row in (await self.session.execute(fallback_stmt)).all()]
        return {row[0]: float(row[1]) for row in rows}

    async def create_summary(
        self,
        *,
        tenant_id: UUID,
        memory_id: UUID,
        summary_text: str,
        source_chunk_count: int,
        metadata: dict | None,
    ) -> MemorySummary:
        summary_hash = hashlib.sha256(summary_text.encode("utf-8")).hexdigest()
        entity = MemorySummary(
            tenant_id=tenant_id,
            memory_id=memory_id,
            summary_text=summary_text,
            summary_hash=summary_hash,
            source_chunk_count=source_chunk_count,
            token_count=len(summary_text.split()),
            metadata_json=metadata,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def list_memory_chunks(self, *, tenant_id: UUID, memory_id: UUID) -> list[MemoryChunk]:
        stmt = (
            select(MemoryChunk)
            .where(
                MemoryChunk.tenant_id == tenant_id,
                MemoryChunk.memory_id == memory_id,
                MemoryChunk.deleted_at.is_(None),
            )
            .order_by(MemoryChunk.chunk_index.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_memory(self, *, tenant_id: UUID, memory_id: UUID) -> AIMemory | None:
        stmt = select(AIMemory).where(
            AIMemory.tenant_id == tenant_id,
            AIMemory.id == memory_id,
            AIMemory.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_conversation_context(
        self,
        *,
        tenant_id: UUID,
        conversation_id: UUID,
        context_text: str,
        token_budget: int,
        tokens_used: int,
        metadata: dict | None,
    ) -> ConversationContext:
        entity = ConversationContext(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            context_text=context_text,
            token_budget=token_budget,
            tokens_used=tokens_used,
            metadata_json=metadata,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def log_retrieval(
        self,
        *,
        tenant_id: UUID,
        conversation_id: UUID | None,
        query_text: str,
        retrieval_mode: str,
        top_k: int,
        latency_ms: int,
        result_count: int,
        metadata: dict | None,
    ) -> None:
        query_hash = hashlib.sha256(query_text.encode("utf-8")).hexdigest()
        entity = MemoryRetrievalLog(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            query_text=query_text,
            query_hash=query_hash,
            retrieval_mode=retrieval_mode,
            top_k=top_k,
            latency_ms=latency_ms,
            result_count=result_count,
            metadata_json=metadata,
        )
        self.session.add(entity)
        await self.session.flush()

    async def soft_delete_memory(self, *, tenant_id: UUID, memory_id: UUID) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(AIMemory)
            .where(AIMemory.tenant_id == tenant_id, AIMemory.id == memory_id, AIMemory.deleted_at.is_(None))
            .values(deleted_at=now)
        )
        chunk_stmt = (
            update(MemoryChunk)
            .where(MemoryChunk.tenant_id == tenant_id, MemoryChunk.memory_id == memory_id, MemoryChunk.deleted_at.is_(None))
            .values(deleted_at=now)
        )
        summary_stmt = (
            update(MemorySummary)
            .where(MemorySummary.tenant_id == tenant_id, MemorySummary.memory_id == memory_id, MemorySummary.deleted_at.is_(None))
            .values(deleted_at=now)
        )
        result = await self.session.execute(stmt)
        await self.session.execute(chunk_stmt)
        await self.session.execute(summary_stmt)
        return result.rowcount > 0

    async def hard_delete_memory(self, *, tenant_id: UUID, memory_id: UUID) -> bool:
        await self.session.execute(delete(MemoryChunk).where(MemoryChunk.tenant_id == tenant_id, MemoryChunk.memory_id == memory_id))
        await self.session.execute(delete(MemorySummary).where(MemorySummary.tenant_id == tenant_id, MemorySummary.memory_id == memory_id))
        result = await self.session.execute(delete(AIMemory).where(AIMemory.tenant_id == tenant_id, AIMemory.id == memory_id))
        return result.rowcount > 0

    async def analytics(self, *, tenant_id: UUID) -> dict[str, Any]:
        memories_stmt = select(func.count()).select_from(AIMemory).where(AIMemory.tenant_id == tenant_id, AIMemory.deleted_at.is_(None))
        chunks_stmt = select(func.count()).select_from(MemoryChunk).where(MemoryChunk.tenant_id == tenant_id, MemoryChunk.deleted_at.is_(None))
        summaries_stmt = select(func.count()).select_from(MemorySummary).where(MemorySummary.tenant_id == tenant_id, MemorySummary.deleted_at.is_(None))
        avg_chunk_stmt = select(func.avg(MemoryChunk.token_count)).where(MemoryChunk.tenant_id == tenant_id, MemoryChunk.deleted_at.is_(None))
        types_stmt = (
            select(AIMemory.memory_type, func.count().label("count"))
            .where(AIMemory.tenant_id == tenant_id, AIMemory.deleted_at.is_(None))
            .group_by(AIMemory.memory_type)
        )

        total_memories = int((await self.session.execute(memories_stmt)).scalar() or 0)
        total_chunks = int((await self.session.execute(chunks_stmt)).scalar() or 0)
        total_summaries = int((await self.session.execute(summaries_stmt)).scalar() or 0)
        avg_chunk_tokens = float((await self.session.execute(avg_chunk_stmt)).scalar() or 0.0)

        type_rows = (await self.session.execute(types_stmt)).all()
        top_memory_types = {str(row[0]): int(row[1]) for row in type_rows}

        return {
            "total_memories": total_memories,
            "total_chunks": total_chunks,
            "total_summaries": total_summaries,
            "avg_chunk_tokens": avg_chunk_tokens,
            "top_memory_types": top_memory_types,
        }
