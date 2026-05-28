"""Reconnect and replay service for stream recovery.

Handles:
- Reconnect session initialization
- Retrieval of pending/unacked messages for replay
- Resume token generation and validation
- Message acknowledgment tracking
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from jose import jwt, JWTError
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import ReconnectSession, StreamingChunk, MessageAcknowledgment
from app.models.ai_messages import AIMessage
from app.db.base import UUIDPrimaryKeyMixin

logger = logging.getLogger(__name__)


class ReconnectService:
    """Service for managing reconnect and replay scenarios."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.resume_token_ttl_minutes = 30  # Resume tokens valid for 30 minutes

    async def create_or_get_reconnect_session(
        self,
        tenant_id: UUID,
        session_id: UUID,
        conversation_id: UUID,
    ) -> ReconnectSession:
        """Create or retrieve reconnect session state.
        
        Args:
            tenant_id: Tenant ID for isolation
            session_id: User session ID
            conversation_id: Conversation being accessed
            
        Returns:
            ReconnectSession record
        """
        stmt = select(ReconnectSession).where(
            and_(
                ReconnectSession.session_id == session_id,
                ReconnectSession.conversation_id == conversation_id,
            )
        )
        
        result = await self.db.execute(stmt)
        reconnect_session = result.scalar_one_or_none()
        
        if reconnect_session:
            return reconnect_session
        
        # Create new
        reconnect_session = ReconnectSession(
            id=UUIDPrimaryKeyMixin.generate_id(),
            tenant_id=tenant_id,
            session_id=session_id,
            conversation_id=conversation_id,
            last_acked_message_sequence_no=0,
            last_acked_chunk_sequence_no=0,
            pending_replay_count=0,
        )
        
        self.db.add(reconnect_session)
        await self.db.flush()
        
        return reconnect_session

    async def generate_resume_token(
        self,
        tenant_id: UUID,
        session_id: UUID,
        conversation_id: UUID,
        last_acked_message_no: int,
    ) -> str:
        """Generate a resume token for reconnect.
        
        Resume tokens encode session state and allow clients to resume
        exactly where they left off.
        
        Args:
            tenant_id: Tenant ID
            session_id: Session ID
            conversation_id: Conversation ID
            last_acked_message_no: Last acknowledged message sequence number
            
        Returns:
            JWT token
        """
        expires = datetime.utcnow() + timedelta(minutes=self.resume_token_ttl_minutes)
        
        payload = {
            "sub": str(session_id),
            "tenant_id": str(tenant_id),
            "conversation_id": str(conversation_id),
            "last_acked_message_no": last_acked_message_no,
            "exp": expires,
            "type": "resume",
        }
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        
        logger.info(
            "resume_token_generated",
            extra={
                "session_id": str(session_id),
                "conversation_id": str(conversation_id),
                "expires_at": expires.isoformat(),
            },
        )
        
        return token

    async def validate_resume_token(
        self,
        token: str,
    ) -> Optional[dict]:
        """Validate and decode a resume token.
        
        Args:
            token: JWT resume token
            
        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            
            if payload.get("type") != "resume":
                logger.warning("invalid_resume_token_type")
                return None
            
            return payload
            
        except JWTError as e:
            logger.warning("resume_token_validation_failed", extra={"error": str(e)})
            return None

    async def record_message_acknowledgment(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
        user_id: UUID,
        session_id: UUID,
        message_sequence_no: int,
        last_chunk_sequence_no: int,
    ) -> MessageAcknowledgment:
        """Record client acknowledgment of a message.
        
        Args:
            tenant_id: Tenant ID
            conversation_id: Conversation ID
            user_id: User ID
            session_id: Session ID
            message_sequence_no: Message sequence number being acked
            last_chunk_sequence_no: Last chunk sequence acked
            
        Returns:
            Created MessageAcknowledgment record
        """
        ack = MessageAcknowledgment(
            id=UUIDPrimaryKeyMixin.generate_id(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            user_id=user_id,
            session_id=session_id,
            message_sequence_no=message_sequence_no,
            last_chunk_sequence_no=last_chunk_sequence_no,
        )
        
        self.db.add(ack)
        await self.db.flush()
        
        # Update reconnect session
        reconnect_session = await self.create_or_get_reconnect_session(
            tenant_id=tenant_id,
            session_id=session_id,
            conversation_id=conversation_id,
        )
        
        if message_sequence_no > reconnect_session.last_acked_message_sequence_no:
            reconnect_session.last_acked_message_sequence_no = message_sequence_no
            reconnect_session.last_acked_chunk_sequence_no = last_chunk_sequence_no
            reconnect_session.updated_at = datetime.utcnow()
            await self.db.flush()
        
        logger.info(
            "message_acknowledged",
            extra={
                "session_id": str(session_id),
                "message_sequence_no": message_sequence_no,
            },
        )
        
        return ack

    async def get_pending_replay(
        self,
        tenant_id: UUID,
        session_id: UUID,
        conversation_id: UUID,
        from_sequence_no: int,
    ) -> list[dict]:
        """Retrieve unacked messages and chunks for replay.
        
        When a client reconnects, it provides the last sequence number it saw.
        This method retrieves all messages after that point that need to be
        replayed.
        
        Args:
            tenant_id: Tenant ID for isolation
            session_id: Session ID
            conversation_id: Conversation ID
            from_sequence_no: Start from this sequence number (exclusive)
            
        Returns:
            List of replay events (message chunks and completions)
        """
        # Get all messages after from_sequence_no
        stmt = (
            select(AIMessage)
            .where(
                and_(
                    AIMessage.tenant_id == tenant_id,
                    AIMessage.conversation_id == conversation_id,
                    AIMessage.sequence_no > from_sequence_no,
                )
            )
            .order_by(AIMessage.sequence_no)
        )
        
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        replay_events: list[dict] = []
        
        for message in messages:
            # For each message, get its chunks
            chunk_stmt = (
                select(StreamingChunk)
                .where(StreamingChunk.message_id == message.id)
                .order_by(StreamingChunk.chunk_index)
            )
            
            chunk_result = await self.db.execute(chunk_stmt)
            chunks = chunk_result.scalars().all()
            
            # Add chunk events
            for chunk in chunks:
                replay_events.append({
                    "type": "message_chunk",
                    "message_id": str(message.id),
                    "sequence_no": chunk.sequence_no,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "delta_tokens": chunk.delta_tokens,
                })
            
            # Add completion event
            replay_events.append({
                "type": "message_complete",
                "message_id": str(message.id),
                "sequence_no": message.sequence_no,
                "total_tokens": message.token_count or 0,
            })
        
        logger.info(
            "replay_prepared",
            extra={
                "session_id": str(session_id),
                "from_sequence_no": from_sequence_no,
                "replay_events": len(replay_events),
            },
        )
        
        return replay_events

    async def cleanup_old_reconnect_sessions(
        self,
        older_than_hours: int = 24,
    ) -> int:
        """Clean up old reconnect sessions that have expired.
        
        Args:
            older_than_hours: Delete sessions older than N hours
            
        Returns:
            Number of records deleted
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        
        stmt = select(ReconnectSession).where(
            ReconnectSession.resume_token_expires_at < cutoff_time
        )
        
        result = await self.db.execute(stmt)
        old_sessions = result.scalars().all()
        
        for session in old_sessions:
            await self.db.delete(session)
        
        await self.db.flush()
        
        count = len(old_sessions)
        logger.info(
            "reconnect_sessions_cleaned",
            extra={"deleted_count": count, "older_than_hours": older_than_hours},
        )
        
        return count
