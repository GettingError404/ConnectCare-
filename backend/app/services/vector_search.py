"""Vector search and embedding service for semantic memory retrieval.

Handles:
- Text embedding generation
- Vector similarity search
- Embedding indexing and maintenance
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_memory import AIMemoryEmbedding, AIMemorySummary, EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Service for vector embedding and semantic search."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self._embedding_model = None

    @property
    def embedding_model(self):
        """Lazy load embedding model."""
        if self._embedding_model is None:
            try:
                import openai
                # Note: Configure OPENAI_API_KEY in environment
                self._embedding_model = "text-embedding-3-small"  # OpenAI model
            except Exception:
                logger.warning("embedding_model_not_configured")
                return None
        return self._embedding_model

    async def embed_text(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> list[float]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            model: Optional embedding model name (defaults to configured model)
            
        Returns:
            Embedding vector (list of floats)
            
        Raises:
            ValueError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        
        model = model or self.embedding_model
        if not model:
            raise ValueError("No embedding model configured")
        
        try:
            # Use OpenAI API if available
            import openai
            
            response = await openai.AsyncOpenAI().embeddings.create(
                input=text,
                model=model,
            )
            
            embedding = response.data[0].embedding
            
            # Validate dimension
            if len(embedding) != EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Unexpected embedding dimension: {len(embedding)} "
                    f"(expected {EMBEDDING_DIMENSION})"
                )
            
            logger.debug("text_embedded", extra={"text_length": len(text), "model": model})
            
            return embedding
            
        except Exception as e:
            logger.exception("embedding_generation_failed", extra={"model": model, "error": str(e)})
            raise ValueError(f"Failed to generate embedding: {e}")

    async def store_embedding(
        self,
        tenant_id: UUID,
        memory_summary_id: UUID,
        embedding: list[float],
    ) -> AIMemoryEmbedding:
        """Store embedding for a memory summary.
        
        Args:
            tenant_id: Tenant ID for isolation
            memory_summary_id: Memory summary to embed
            embedding: Embedding vector
            
        Returns:
            Created AIMemoryEmbedding record
        """
        from app.db.base import UUIDPrimaryKeyMixin
        
        if len(embedding) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Invalid embedding dimension: {len(embedding)} "
                f"(expected {EMBEDDING_DIMENSION})"
            )
        
        memory_embedding = AIMemoryEmbedding(
            id=UUIDPrimaryKeyMixin.generate_id(),
            tenant_id=tenant_id,
            memory_summary_id=memory_summary_id,
            embedding=embedding,
        )
        
        self.db.add(memory_embedding)
        await self.db.flush()
        
        logger.info(
            "embedding_stored",
            extra={"memory_summary_id": str(memory_summary_id)},
        )
        
        return memory_embedding

    async def search_similar(
        self,
        tenant_id: UUID,
        query: str,
        conversation_id: Optional[UUID] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[dict]:
        """Search for similar memories using semantic similarity.
        
        Args:
            tenant_id: Tenant ID for isolation
            query: Query text to search for
            conversation_id: Optional - scope search to specific conversation
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of similar memories with scores, ranked by relevance
        """
        # Generate query embedding
        try:
            query_embedding = await self.embed_text(query)
        except Exception as e:
            logger.warning("search_failed_embedding", extra={"error": str(e)})
            return []
        
        # Search using pgvector
        from sqlalchemy.sql import func
        
        # Cosine distance query
        stmt = (
            select(
                AIMemorySummary,
                AIMemoryEmbedding.embedding,
                func.cosine_distance(
                    AIMemoryEmbedding.embedding,
                    query_embedding,
                ).label("distance")
            )
            .join(
                AIMemoryEmbedding,
                AIMemoryEmbedding.memory_summary_id == AIMemorySummary.id
            )
            .where(AIMemorySummary.tenant_id == tenant_id)
        )
        
        # Filter by conversation if provided
        if conversation_id:
            stmt = stmt.where(AIMemorySummary.conversation_id == conversation_id)
        
        stmt = stmt.order_by("distance").limit(limit)
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        # Build results with similarity scores
        results = []
        for memory, embedding, distance in rows:
            similarity = 1 - distance  # Convert distance to similarity
            
            if similarity < similarity_threshold:
                continue
            
            results.append({
                "id": str(memory.id),
                "text": memory.summary_text,
                "similarity": similarity,
                "conversation_id": str(memory.conversation_id),
                "created_at": memory.created_at.isoformat() if memory.created_at else None,
            })
        
        logger.info(
            "semantic_search_completed",
            extra={
                "query_length": len(query),
                "results": len(results),
                "threshold": similarity_threshold,
            },
        )
        
        return results

    async def reindex_conversation(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
    ) -> int:
        """Regenerate embeddings for all memories in a conversation.
        
        Useful after model updates or corrections.
        
        Args:
            tenant_id: Tenant ID
            conversation_id: Conversation to reindex
            
        Returns:
            Number of embeddings regenerated
        """
        # Get all summaries in conversation
        stmt = select(AIMemorySummary).where(
            and_(
                AIMemorySummary.tenant_id == tenant_id,
                AIMemorySummary.conversation_id == conversation_id,
            )
        )
        
        result = await self.db.execute(stmt)
        summaries = result.scalars().all()
        
        reindexed_count = 0
        
        for summary in summaries:
            try:
                # Generate new embedding
                embedding = await self.embed_text(summary.summary_text)
                
                # Delete old embedding
                old_embedding_stmt = select(AIMemoryEmbedding).where(
                    AIMemoryEmbedding.memory_summary_id == summary.id
                )
                old_result = await self.db.execute(old_embedding_stmt)
                old_embedding = old_result.scalar_one_or_none()
                
                if old_embedding:
                    await self.db.delete(old_embedding)
                
                # Store new embedding
                await self.store_embedding(tenant_id, summary.id, embedding)
                reindexed_count += 1
                
            except Exception as e:
                logger.warning(
                    "reindex_failed",
                    extra={"summary_id": str(summary.id), "error": str(e)},
                )
                continue
        
        await self.db.commit()
        
        logger.info(
            "conversation_reindexed",
            extra={
                "conversation_id": str(conversation_id),
                "reindexed_count": reindexed_count,
            },
        )
        
        return reindexed_count

    async def bulk_embed_and_store(
        self,
        tenant_id: UUID,
        memories: list[tuple[UUID, str]],  # List of (memory_id, text) pairs
    ) -> int:
        """Bulk embed and store embeddings for multiple memories.
        
        Used during batch processing to efficiently generate embeddings.
        
        Args:
            tenant_id: Tenant ID
            memories: List of (memory_summary_id, text) tuples
            
        Returns:
            Number of embeddings successfully created
        """
        stored_count = 0
        
        for memory_id, text in memories:
            try:
                embedding = await self.embed_text(text)
                await self.store_embedding(tenant_id, memory_id, embedding)
                stored_count += 1
            except Exception as e:
                logger.warning(
                    "bulk_embed_failed",
                    extra={"memory_id": str(memory_id), "error": str(e)},
                )
                continue
        
        await self.db.commit()
        
        logger.info(
            "bulk_embed_completed",
            extra={"total": len(memories), "stored": stored_count},
        )
        
        return stored_count
