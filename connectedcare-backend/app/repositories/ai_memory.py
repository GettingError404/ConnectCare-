"""AI Memory Persistence Repository Layer

Provides thin data-access interface for AI memory models.
All methods enforce mandatory tenant_id filtering for multi-tenant isolation.
Repository layer contains NO business logic — only CRUD and query operations.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.ai_memory import (
    AIConversation,
    AIMessage,
    AIMemoryChunk,
    AIMemoryEmbedding,
    AIMemorySummary,
    AIContextWindow,
    AIMemoryLink,
    EMBEDDING_DIMENSION,
)


class AIMemoryRepository:
    """Thin repository for AI memory persistence.
    
    Purpose:
    - Encapsulate data access patterns for AI memory models
    - Enforce mandatory tenant isolation in all queries
    - Provide query building blocks for service-layer consumption
    
    Requirements:
    - Every method filters by tenant_id explicitly
    - No business logic (computation, validation, transformation)
    - SQLAlchemy Session-based (synchronous, eager load via selectin strategy)
    - Production-safe: deterministic ordering, NULL-safe comparisons, indexed columns
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== Conversation Operations ====================

    def create_conversation(
        self,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        title: Optional[str] = None,
        conversation_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AIConversation:
        """Create a new conversation.
        
        Args:
            tenant_id: Tenant UUID (mandatory)
            user_id: User UUID (optional, can be null for system-initiated)
            title: Conversation title
            conversation_type: Type classifier (e.g., 'session', 'document_qa', 'diagnostic')
            metadata: JSONB metadata dict
            
        Returns:
            Created AIConversation instance
        """
        conversation = AIConversation(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            conversation_type=conversation_type,
            metadata_json=metadata,
            status="active",
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation(self, tenant_id: UUID, conversation_id: UUID) -> Optional[AIConversation]:
        """Retrieve conversation by ID with tenant isolation.
        
        Args:
            tenant_id: Tenant UUID (mandatory filter)
            conversation_id: Conversation UUID
            
        Returns:
            AIConversation or None if not found or tenant mismatch
        """
        return self.db.query(AIConversation).filter(
            and_(
                AIConversation.tenant_id == tenant_id,
                AIConversation.id == conversation_id,
                AIConversation.deleted_at.is_(None),
            )
        ).first()

    def soft_delete_conversation(self, tenant_id: UUID, conversation_id: UUID) -> bool:
        """Soft-delete conversation and cascade to related entities.
        
        Sets deleted_at timestamp on conversation; cascade rules in schema will handle
        soft-delete propagation to messages, summaries, chunks, embeddings, etc.
        (For now, we set deleted_at on this entity only; service layer can orchestrate
        cascading soft deletes if needed for compliance requirements.)
        
        Args:
            tenant_id: Tenant UUID (mandatory filter)
            conversation_id: Conversation UUID
            
        Returns:
            True if soft-deleted, False if not found or already deleted
        """
        conversation = self.get_conversation(tenant_id, conversation_id)
        if not conversation:
            return False
        conversation.deleted_at = datetime.utcnow()
        self.db.add(conversation)
        self.db.commit()
        return True

    # ==================== Message Operations ====================

    def append_message(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        role: str,
        content: str,
        content_hash: str,
        token_count: Optional[int] = None,
        recorded_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> AIMessage:
        """Append message to conversation (immutable ledger entry).
        
        Args:
            tenant_id: Tenant UUID (mandatory)
            conversation_id: Conversation UUID (validates existence via FK)
            role: Message role (e.g., 'user', 'assistant', 'system')
            content: Message text content
            content_hash: SHA256 or similar hash of content (caller computes)
            token_count: Token count for LLM accounting
            recorded_at: Explicit timestamp (defaults to now if None)
            metadata: JSONB metadata dict
            
        Returns:
            Created AIMessage instance
        """
        message = AIMessage(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            content_hash=content_hash,
            token_count=token_count,
            recorded_at=recorded_at or datetime.utcnow(),
            metadata_json=metadata,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_recent_messages(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        limit: int = 50,
    ) -> list[AIMessage]:
        """Retrieve recent messages from conversation.
        
        Ordered by recorded_at DESC (most recent first), excludes soft-deleted.
        
        Args:
            tenant_id: Tenant UUID (mandatory filter)
            conversation_id: Conversation UUID
            limit: Maximum messages to retrieve
            
        Returns:
            List of AIMessage instances (newest first)
        """
        return self.db.query(AIMessage).filter(
            and_(
                AIMessage.tenant_id == tenant_id,
                AIMessage.conversation_id == conversation_id,
                AIMessage.deleted_at.is_(None),
            )
        ).order_by(AIMessage.recorded_at.desc()).limit(limit).all()

    # ==================== Summary Operations ====================

    def create_summary(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        summary_text: str,
        summary_hash: str,
        source_window_start_at: Optional[datetime] = None,
        source_window_end_at: Optional[datetime] = None,
        summary_version: str = "v1",
        metadata: Optional[dict] = None,
    ) -> AIMemorySummary:
        """Create a memory summary (compressed conversation window).
        
        Args:
            tenant_id: Tenant UUID (mandatory)
            conversation_id: Conversation UUID
            summary_text: Compressed summary text
            summary_hash: SHA256 or similar hash of summary text
            source_window_start_at: Start of summarized window (optional audit)
            source_window_end_at: End of summarized window (optional audit)
            summary_version: Version string for re-summarization tracking
            metadata: JSONB metadata dict
            
        Returns:
            Created AIMemorySummary instance
        """
        summary = AIMemorySummary(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            summary_text=summary_text,
            summary_hash=summary_hash,
            source_window_start_at=source_window_start_at,
            source_window_end_at=source_window_end_at,
            summary_version=summary_version,
            metadata_json=metadata,
        )
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        return summary

    def get_conversation_summaries(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
    ) -> list[AIMemorySummary]:
        """Retrieve all summaries for conversation (excludes soft-deleted).
        
        Args:
            tenant_id: Tenant UUID (mandatory filter)
            conversation_id: Conversation UUID
            
        Returns:
            List of AIMemorySummary instances (ordered by source_window_end_at DESC)
        """
        return self.db.query(AIMemorySummary).filter(
            and_(
                AIMemorySummary.tenant_id == tenant_id,
                AIMemorySummary.conversation_id == conversation_id,
                AIMemorySummary.deleted_at.is_(None),
            )
        ).order_by(AIMemorySummary.source_window_end_at.desc()).all()

    # ==================== Chunk Operations ====================

    def create_chunk(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        chunk_text: str,
        chunk_hash: str,
        chunk_index: int,
        chunk_type: str = "message",
        message_id: Optional[UUID] = None,
        summary_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> AIMemoryChunk:
        """Create a retrieval chunk (retrieval unit for semantic search).
        
        Args:
            tenant_id: Tenant UUID (mandatory)
            conversation_id: Conversation UUID
            chunk_text: Chunk text content
            chunk_hash: SHA256 or similar hash of chunk text
            chunk_index: Position index in sequence
            chunk_type: Type classifier (default 'message', can be 'summary', 'context', etc.)
            message_id: Parent message UUID (mutually exclusive with summary_id)
            summary_id: Parent summary UUID (mutually exclusive with message_id)
            metadata: JSONB metadata dict
            
        Returns:
            Created AIMemoryChunk instance
            
        Raises:
            IntegrityError if neither message_id nor summary_id is provided (CHECK constraint)
        """
        chunk = AIMemoryChunk(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            chunk_text=chunk_text,
            chunk_hash=chunk_hash,
            chunk_index=chunk_index,
            chunk_type=chunk_type,
            message_id=message_id,
            summary_id=summary_id,
            metadata_json=metadata,
        )
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def get_chunk(self, tenant_id: UUID, chunk_id: UUID) -> Optional[AIMemoryChunk]:
        """Retrieve chunk by ID with tenant isolation.
        
        Args:
            tenant_id: Tenant UUID (mandatory filter)
            chunk_id: Chunk UUID
            
        Returns:
            AIMemoryChunk or None if not found or tenant mismatch
        """
        return self.db.query(AIMemoryChunk).filter(
            and_(
                AIMemoryChunk.tenant_id == tenant_id,
                AIMemoryChunk.id == chunk_id,
                AIMemoryChunk.deleted_at.is_(None),
            )
        ).first()

    # ==================== Embedding Operations ====================

    def store_embedding(
        self,
        tenant_id: UUID,
        chunk_id: UUID,
        embedding: list[float],
        embedding_model: str,
        content_hash: str,
        embedding_version: str = "v1",
        metadata: Optional[dict] = None,
        embedded_at: Optional[datetime] = None,
    ) -> AIMemoryEmbedding:
        """Store vector embedding for chunk (semantic search index).
        
        Args:
            tenant_id: Tenant UUID (mandatory)
            chunk_id: Chunk UUID (validates existence via FK)
            embedding: Vector as list of floats (1536 dims for OpenAI/text-embedding-3-small)
            embedding_model: Model identifier (e.g., 'text-embedding-3-small')
            content_hash: SHA256 or similar hash of chunk content (for re-embedding detection)
            embedding_version: Version string for model versioning
            metadata: JSONB metadata dict
            embedded_at: Explicit timestamp (defaults to now if None)
            
        Returns:
            Created AIMemoryEmbedding instance
        """
        emb_obj = AIMemoryEmbedding(
            tenant_id=tenant_id,
            chunk_id=chunk_id,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            embedding_dimension=len(embedding),
            content_hash=content_hash,
            metadata_json=metadata,
            embedded_at=embedded_at or datetime.utcnow(),
        )
        self.db.add(emb_obj)
        self.db.commit()
        self.db.refresh(emb_obj)
        return emb_obj

    def get_embedding(self, tenant_id: UUID, chunk_id: UUID) -> Optional[AIMemoryEmbedding]:
        """Retrieve embedding for chunk (most recent, excludes soft-deleted).
        
        Args:
            tenant_id: Tenant UUID (mandatory filter)
            chunk_id: Chunk UUID
            
        Returns:
            AIMemoryEmbedding or None if not found
        """
        return self.db.query(AIMemoryEmbedding).filter(
            and_(
                AIMemoryEmbedding.tenant_id == tenant_id,
                AIMemoryEmbedding.chunk_id == chunk_id,
                AIMemoryEmbedding.deleted_at.is_(None),
            )
        ).order_by(AIMemoryEmbedding.embedded_at.desc()).first()

    # ==================== Semantic Search ====================

    def semantic_search(
        self,
        tenant_id: UUID,
        embedding_vector: list[float],
        limit: int = 10,
        similarity_threshold: float = 0.0,
    ) -> list[tuple[AIMemoryChunk, float]]:
        """Semantic search via vector similarity (cosine distance).
        
        Returns chunks ranked by cosine similarity to query embedding.
        Uses pgvector ivfflat index for efficient similarity search.
        
        Args:
            tenant_id: Tenant UUID (mandatory filter)
            embedding_vector: Query embedding vector (list of floats)
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score (0.0 to 1.0, cosine)
            
        Returns:
            List of tuples (AIMemoryChunk, similarity_score) ordered by similarity DESC
        """
        # Construct raw SQL for cosine similarity via pgvector
        # Using <=> operator for distance (lower = more similar)
        # Similarity = 1 - distance for cosine
        from sqlalchemy import literal_column, text

        embedding_str = str(embedding_vector)
        
        # Raw query for pgvector semantic search with tenant filter
        query_text = f"""
            SELECT 
                c.id, 
                c.created_at,
                c.updated_at,
                c.tenant_id,
                c.conversation_id,
                c.message_id,
                c.summary_id,
                c.chunk_index,
                c.chunk_text,
                c.chunk_hash,
                c.chunk_type,
                c.metadata,
                c.deleted_at,
                1 - (e.embedding <=> %s::vector) AS similarity
            FROM ai_memory_chunks c
            INNER JOIN ai_memory_embeddings e ON c.id = e.chunk_id
            WHERE c.tenant_id = %s
            AND c.deleted_at IS NULL
            AND e.deleted_at IS NULL
            AND (1 - (e.embedding <=> %s::vector)) >= %s
            ORDER BY e.embedding <=> %s::vector ASC
            LIMIT %s
        """
        
        # Use text() for raw SQL query
        result = self.db.execute(
            text(query_text),
            (embedding_str, str(tenant_id), embedding_str, similarity_threshold, embedding_str, limit)
        )
        
        rows = result.fetchall()
        
        # Reconstruct AIMemoryChunk objects and pair with similarity scores
        results = []
        for row in rows:
            chunk = AIMemoryChunk(
                id=row[0],
                created_at=row[1],
                updated_at=row[2],
                tenant_id=row[3],
                conversation_id=row[4],
                message_id=row[5],
                summary_id=row[6],
                chunk_index=row[7],
                chunk_text=row[8],
                chunk_hash=row[9],
                chunk_type=row[10],
                metadata_json=row[11],
                deleted_at=row[12],
            )
            similarity_score = float(row[13])
            results.append((chunk, similarity_score))
        
        return results

    # ==================== Link Operations ====================

    def create_link(
        self,
        tenant_id: UUID,
        source_type: str,
        source_id: UUID,
        target_type: str,
        target_id: UUID,
        relation_type: str,
        weight: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> AIMemoryLink:
        """Create provenance link between entities (e.g., chunk -> original message).
        
        Args:
            tenant_id: Tenant UUID (mandatory)
            source_type: Type of source entity (e.g., 'chunk', 'summary')
            source_id: UUID of source entity
            target_type: Type of target entity (e.g., 'message', 'context_window')
            target_id: UUID of target entity
            relation_type: Relation label (e.g., 'derived_from', 'references', 'parent_of')
            weight: Optional edge weight for graph algorithms
            metadata: JSONB metadata dict
            
        Returns:
            Created AIMemoryLink instance
        """
        link = AIMemoryLink(
            tenant_id=tenant_id,
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            metadata_json=metadata,
        )
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def get_links_by_source(
        self,
        tenant_id: UUID,
        source_type: str,
        source_id: UUID,
    ) -> list[AIMemoryLink]:
        """Retrieve outgoing links from source entity.
        
        Args:
            tenant_id: Tenant UUID (mandatory filter)
            source_type: Type of source entity
            source_id: UUID of source entity
            
        Returns:
            List of AIMemoryLink instances (excludes soft-deleted)
        """
        return self.db.query(AIMemoryLink).filter(
            and_(
                AIMemoryLink.tenant_id == tenant_id,
                AIMemoryLink.source_type == source_type,
                AIMemoryLink.source_id == source_id,
                AIMemoryLink.deleted_at.is_(None),
            )
        ).all()

    def get_links_by_target(
        self,
        tenant_id: UUID,
        target_type: str,
        target_id: UUID,
    ) -> list[AIMemoryLink]:
        """Retrieve incoming links to target entity.
        
        Args:
            tenant_id: Tenant UUID (mandatory filter)
            target_type: Type of target entity
            target_id: UUID of target entity
            
        Returns:
            List of AIMemoryLink instances (excludes soft-deleted)
        """
        return self.db.query(AIMemoryLink).filter(
            and_(
                AIMemoryLink.tenant_id == tenant_id,
                AIMemoryLink.target_type == target_type,
                AIMemoryLink.target_id == target_id,
                AIMemoryLink.deleted_at.is_(None),
            )
        ).all()
