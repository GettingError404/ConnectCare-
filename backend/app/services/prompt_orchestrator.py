"""Prompt orchestration service for building optimal AI prompts.

Combines system prompts, user context, conversation history, and
semantic memories into a single optimized prompt for the AI agent.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.conversation_context import ConversationContextService
from app.services.vector_search import VectorSearchService

logger = logging.getLogger(__name__)


class PromptOrchestratorService:
    """Service for building optimized prompts for AI agents."""

    def __init__(
        self,
        db_session: AsyncSession,
        context_service: ConversationContextService,
        vector_service: VectorSearchService,
    ):
        self.db = db_session
        self.context_service = context_service
        self.vector_service = vector_service

    async def orchestrate_prompt(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        user_message: str,
        user_profile: Optional[dict] = None,
        system_prompt: Optional[str] = None,
        token_budget: int = 2000,
        include_semantic_memories: bool = True,
    ) -> dict:
        """Build complete prompt with all context layers.
        
        Orchestrates the complete prompt building pipeline:
        1. System prompt (instructions, tone, behavior)
        2. User profile context (demographics, preferences, history)
        3. Recent conversation history (last N messages)
        4. Semantic memories (vector-retrieved relevant context)
        5. Current user message
        
        Args:
            tenant_id: Tenant ID for isolation
            conversation_id: Conversation ID
            user_message: Current user input
            user_profile: User profile/context dict
            system_prompt: Custom system prompt (optional)
            token_budget: Total token budget for context
            include_semantic_memories: Whether to retrieve vector-based memories
            
        Returns:
            Dict with:
            - "system_prompt": string
            - "messages": list of message dicts with role/content
            - "metadata": dict with context building metadata
        """
        # Set default system prompt for healthcare context
        if not system_prompt:
            system_prompt = (
                "You are an empathetic healthcare assistant helping patients manage their health. "
                "Provide clear, medically accurate guidance while encouraging users to consult healthcare providers for serious concerns. "
                "Be conversational and supportive."
            )
        
        # Generate embedding for current message if semantic search enabled
        current_embedding: Optional[list[float]] = None
        if include_semantic_memories:
            try:
                current_embedding = await self.vector_service.embed_text(user_message)
            except Exception as e:
                logger.warning("failed_to_embed_message", extra={"error": str(e)})
                current_embedding = None
        
        # Build user context string
        user_context_str = ""
        if user_profile:
            parts = []
            if profile_name := user_profile.get("name"):
                parts.append(f"Name: {profile_name}")
            if profile_age := user_profile.get("age"):
                parts.append(f"Age: {profile_age}")
            if profile_conditions := user_profile.get("conditions"):
                conditions_str = ", ".join(profile_conditions) if isinstance(profile_conditions, list) else str(profile_conditions)
                parts.append(f"Medical conditions: {conditions_str}")
            if profile_medications := user_profile.get("medications"):
                meds_str = ", ".join(profile_medications) if isinstance(profile_medications, list) else str(profile_medications)
                parts.append(f"Current medications: {meds_str}")
            
            user_context_str = "\n".join(parts)
        
        # Build optimized context using context service
        context = await self.context_service.build_optimized_context(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            current_message=user_message,
            current_embedding=current_embedding,
            token_budget=token_budget,
            system_prompt=system_prompt,
            user_context={"profile": user_context_str} if user_context_str else None,
        )
        
        # Build final messages list
        messages = []
        
        # Add user context as system message if present
        if user_context_str:
            messages.append({
                "role": "system",
                "content": f"User context:\n{user_context_str}",
            })
        
        # Add conversation history from context service
        messages.extend(context["messages"])
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message,
        })
        
        # Prepare metadata
        metadata = {
            **context["context_metadata"],
            "orchestrated_at": logger.name,  # Just for tracking
            "include_semantic_memories": include_semantic_memories,
            "user_profile_included": bool(user_profile),
        }
        
        logger.info(
            "prompt_orchestrated",
            extra={
                "conversation_id": str(conversation_id),
                "message_count": len(messages),
                "total_tokens": metadata.get("total_tokens"),
            },
        )
        
        return {
            "system_prompt": system_prompt,
            "messages": messages,
            "metadata": metadata,
        }

    async def build_minimal_prompt(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        user_message: str,
    ) -> dict:
        """Build a minimal prompt with just recent history (fast path).
        
        Used when we need a quick response without semantic search.
        
        Args:
            tenant_id: Tenant ID
            conversation_id: Conversation ID
            user_message: Current user message
            
        Returns:
            Minimal orchestrated prompt
        """
        return await self.orchestrate_prompt(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            user_message=user_message,
            include_semantic_memories=False,
            token_budget=1500,  # Smaller budget for faster response
        )

    async def build_full_context_prompt(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        user_message: str,
        user_profile: Optional[dict] = None,
    ) -> dict:
        """Build a comprehensive prompt with full context (slow path).
        
        Used for complex queries where full context is valuable.
        
        Args:
            tenant_id: Tenant ID
            conversation_id: Conversation ID
            user_message: Current user message
            user_profile: User profile information
            
        Returns:
            Full orchestrated prompt
        """
        return await self.orchestrate_prompt(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            user_message=user_message,
            user_profile=user_profile,
            include_semantic_memories=True,
            token_budget=3000,  # Larger budget for comprehensive context
        )
