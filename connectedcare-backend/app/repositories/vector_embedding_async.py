from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.pgvector import set_ivfflat_probes
from app.models.document_embedding import DocumentEmbedding
from app.schemas.vector_embedding import SimilaritySearchResult, VectorDocumentCreate


class DocumentEmbeddingAsyncRepository:
    """Async repository for multi-tenant vector writes and similarity queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document_embedding(
        self,
        *,
        tenant_id: UUID,
        payload: VectorDocumentCreate,
    ) -> DocumentEmbedding:
        content_hash = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()

        entity = DocumentEmbedding(
            tenant_id=tenant_id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            content=payload.content,
            content_hash=content_hash,
            embedding_model=payload.embedding_model,
            embedding_dimension=len(payload.embedding),
            embedding=payload.embedding,
            metadata_json=payload.metadata,
        )
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def similarity_search(
        self,
        *,
        tenant_id: UUID,
        query_embedding: list[float],
        top_k: int = 10,
        min_score: float | None = None,
        source_type: str | None = None,
    ) -> list[SimilaritySearchResult]:
        await set_ivfflat_probes(self.session)

        distance_expr = DocumentEmbedding.embedding.cosine_distance(query_embedding)

        stmt = (
            select(DocumentEmbedding, distance_expr.label("distance"))
            .where(
                DocumentEmbedding.tenant_id == tenant_id,
                DocumentEmbedding.deleted_at.is_(None),
            )
            .order_by(distance_expr)
            .limit(top_k)
        )

        if source_type:
            stmt = stmt.where(DocumentEmbedding.source_type == source_type)

        rows = (await self.session.execute(stmt)).all()

        results: list[SimilaritySearchResult] = []
        for entity, distance in rows:
            # Cosine distance in pgvector is in [0, 2] for general vectors; for normalized
            # embeddings, this is usually [0, 1]. Score is represented as (1 - distance).
            score = 1.0 - float(distance)
            if min_score is not None and score < min_score:
                continue
            results.append(
                SimilaritySearchResult(
                    id=entity.id,
                    tenant_id=entity.tenant_id,
                    source_type=entity.source_type,
                    source_id=entity.source_id,
                    content=entity.content,
                    distance=float(distance),
                    score=score,
                )
            )
        return results
