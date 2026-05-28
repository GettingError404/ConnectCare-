"""Conversation context retrieval and optimization service.

Responsible for:
- Retrieving recent conversation history
- Searching semantic memory using vector embeddings
- Token-aware truncation
- Building optimized prompt context
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_memory import AIMessage, AIMemorySummary, AIMemoryEmbedding, EMBEDDING_DIMENSION
from app.models.conversation import ContextWindow, ConversationThread
from app.db.base import UUIDPrimaryKeyMixin

logger = logging.getLogger(__name__)


class ConversationContextService:
    """Service for retrieving and building optimized conversation context."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_recent_messages(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        limit: int = 5,
    ) -> list[AIMessage]:
        """Fetch last N messages from conversation, ordered chronologically.
        
        Args:
            tenant_id: Tenant ID for isolation
            conversation_id: Conversation to query
            limit: Number of recent messages to retrieve
            
        Returns:
            List of AIMessage objects, oldest first
        """
        stmt = (
            select(AIMessage)
            .where(
                and_(
                    AIMessage.tenant_id == tenant_id,
                    AIMessage.conversation_id == conversation_id,
                    AIMessage.deleted_at.is_(None),
                )
            )
            .order_by(desc(AIMessage.sequence_no))
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Return oldest first for chat display
        return list(reversed(messages))

    async def search_semantic_memory(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        embedding: list[float],
        limit: int = 3,
        similarity_threshold: float = 0.7,
    ) -> list[AIMemorySummary]:
        """Vector search for relevant historical context via embeddings.
        
        Uses pgvector cosine similarity to find contextually relevant
        memories for the current message.
        
        Args:
            tenant_id: Tenant ID for isolation
            conversation_id: Conversation to search within
            embedding: Query embedding vector
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of relevant AIMemorySummary objects, ranked by similarity
        """
        if not embedding or len(embedding) != EMBEDDING_DIMENSION:
            logger.warning(
                "invalid_embedding",
                extra={"embedding_dim": len(embedding) if embedding else 0},
            )
            return []

        # Use pgvector cosine similarity
        # Note: This requires pgvector extension in PostgreSQL
        from sqlalchemy.sql import func
        from pgvector.sqlalchemy import Vector
        
        stmt = (
            select(
                AIMemorySummary,
                func.cosine_distance(
                    AIMemoryEmbedding.embedding,
                    embedding,
                ).label("distance")
            )
            .join(AIMemoryEmbedding, 
                  AIMemoryEmbedding.memory_summary_id == AIMemorySummary.id)
            .where(
                and_(
                    AIMemorySummary.tenant_id == tenant_id,
                    AIMemorySummary.conversation_id == conversation_id,
                )
            )
            .order_by("distance")
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        # Filter by threshold
        memories = [
            row[0] for row in rows
            if (1 - row[1]) >= similarity_threshold  # cosine_distance is 1 - similarity
        ]
        
        logger.info(
            "semantic_search_completed",
            extra={
                "conversation_id": str(conversation_id),
                "results": len(memories),
                "threshold": similarity_threshold,
            },
        )
        
        return memories

    async def get_summarized_history(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        exclude_recent_minutes: int = 60,
    ) -> list[AIMemorySummary]:
        """Retrieve summarized long-term memories from conversation.
        
        Excludes very recent summaries (typically already in context window)
        and focuses on older compressed history.
        
        Args:
            tenant_id: Tenant ID for isolation
            conversation_id: Conversation to query
            exclude_recent_minutes: Don't return summaries from last N minutes
            
        Returns:
            List of AIMemorySummary objects, ordered by creation
        """
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=exclude_recent_minutes)
        
        stmt = (
            select(AIMemorySummary)
            .where(
                and_(
                    AIMemorySummary.tenant_id == tenant_id,
                    AIMemorySummary.conversation_id == conversation_id,
                    AIMemorySummary.created_at < cutoff_time,
                )
            )
            .order_by(AIMemorySummary.created_at)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def build_optimized_context(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        current_message: str,
        current_embedding: Optional[list[float]] = None,
        token_budget: int = 2000,
        system_prompt: Optional[str] = None,
        user_context: Optional[dict] = None,
    ) -> dict:
        """Build optimized prompt context respecting token limits.
        
        Algorithm:
        1. Allocate token budget: system_prompt + user_context + current_message
        2. Reserve token budget for response
        3. Add recent messages (recent_N window) to context
        4. If budget allows, add semantic memories via vector search
        5. If budget still allows, add summarized history
        6. Emit metadata about truncation or resource usage
        
        Args:
            tenant_id: Tenant ID for isolation
            conversation_id: Conversation for context building
            current_message: The user's current input message
            current_embedding: Embedding of current message for semantic search
            token_budget: Total token budget for context window
            system_prompt: System prompt to include (counts against budget)
            user_context: User profile context to include (counts against budget)
            
        Returns:
            Dict with keys:
            - "system_prompt": system prompt string
            - "messages": list of message dicts for chat completion
            - "context_metadata": dict with:
              - "total_tokens": estimated token count
              - "truncated": boolean
              - "truncation_reason": string or None
              - "sources": list of context sources used
              - "recent_message_count": number of recent messages included
        """
        import tiktoken
        
        try:
            encoding = tiktoken.encoding_for_model("gpt-4")
        except Exception:
            # Fallback to cl100k_base
            encoding = tiktoken.get_encoding("cl100k_base")
        
        def token_count(text: str) -> int:
            if not text:
                return 0
            return len(encoding.encode(text))
        
        # Initialize context
        context_messages: list[dict] = []
        total_tokens = 0
        truncated = False
        truncation_reason: Optional[str] = None
        context_sources = []
        
        # 1. System prompt (fixed)
        system_prompt = system_prompt or "You are a helpful healthcare assistant."
        system_tokens = token_count(system_prompt)
        total_tokens += system_tokens
        
        # 2. User context (fixed)
        user_context_str = ""
        if user_context:
            user_context_str = str(user_context)
            total_tokens += token_count(user_context_str)
        
        # 3. Current message (fixed)
        current_tokens = token_count(current_message)
        total_tokens += current_tokens
        
        # Reserve ~25% of budget for response generation
        available_for_history = int((token_budget - total_tokens) * 0.75)
        
        if available_for_history <= 0:
            logger.warning(
                "insufficient_token_budget",
                extra={
                    "requested_budget": token_budget,
                    "used_by_system": system_tokens,
                    "used_by_user_context": token_count(user_context_str),
                    "used_by_current": current_tokens,
                },
            )
            truncated = True
            truncation_reason = "insufficient_token_budget"
            context_metadata = {
                "total_tokens": total_tokens,
                "truncated": truncated,
                "truncation_reason": truncation_reason,
                "sources": context_sources,
                "recent_message_count": 0,
            }
            return {
                "system_prompt": system_prompt,
                "messages": context_messages,
                "context_metadata": context_metadata,
            }
        
        # 4. Add recent messages
        recent_messages = await self.get_recent_messages(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            limit=10,  # Fetch more, truncate by tokens
        )
        
        context_sources.append("recent_messages")
        recent_message_count = 0
        history_tokens_used = 0
        
        for msg in recent_messages:
            msg_tokens = token_count(msg.content)
            if history_tokens_used + msg_tokens > available_for_history:
                truncated = True
                truncation_reason = "token_limit_reached"
                break
            
            context_messages.append({
                "role": msg.role,
                "content": msg.content,
            })
            history_tokens_used += msg_tokens
            recent_message_count += 1
        
        total_tokens += history_tokens_used
        
        # 5. Semantic memories (if budget allows and embedding provided)
        if current_embedding and not truncated:
            available_semantic = int(available_for_history * 0.3)  # Max 30% of history budget
            
            semantic_memories = await self.search_semantic_memory(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                embedding=current_embedding,
                limit=3,
                similarity_threshold=0.7,
            )
            
            if semantic_memories:
                context_sources.append("semantic_memories")
                semantic_tokens_used = 0
                
                for memory in semantic_memories:
                    memory_tokens = token_count(memory.summary_text)
                    if semantic_tokens_used + memory_tokens > available_semantic:
                        truncated = True
                        truncation_reason = "token_limit_for_semantic_memories"
                        break
                    
                    context_messages.append({
                        "role": "system",
                        "content": f"[Memory] {memory.summary_text}",
                    })
                    semantic_tokens_used += memory_tokens
                
                total_tokens += semantic_tokens_used
        
        context_metadata = {
            "total_tokens": total_tokens,
            "truncated": truncated,
            "truncation_reason": truncation_reason,
            "sources": context_sources,
            "recent_message_count": recent_message_count,
        }
        
        logger.info(
            "context_built",
            extra={
                "conversation_id": str(conversation_id),
                "total_tokens": total_tokens,
                "truncated": truncated,
                "sources": context_sources,
            },
        )
        
        return {
            "system_prompt": system_prompt,
            "messages": context_messages,
            "context_metadata": context_metadata,
        }

    async def save_context_window(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        recent_count: int,
        total_tokens: int,
        truncated: bool,
        truncation_reason: Optional[str] = None,
    ) -> ContextWindow:
        """Persist context window metadata for audit/analytics.
        
        Args:
            tenant_id: Tenant ID
            conversation_id: Conversation ID
            recent_count: Number of recent messages in context
            total_tokens: Total token count used
            truncated: Whether truncation occurred
            truncation_reason: Reason for truncation if applicable
            
        Returns:
            Created ContextWindow record
        """
        from app.models.conversation import ContextWindow
        
        window = ContextWindow(
            id=UUIDPrimaryKeyMixin.generate_id(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            recent_message_count=recent_count,
            total_tokens_in_window=total_tokens,
            truncated=truncated,
            truncation_reason=truncation_reason,
        )
        
        self.db.add(window)
        await self.db.flush()
        
        return window
