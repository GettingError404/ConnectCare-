"""ORM Validation Tests for AI Memory Models

Tests verify:
- Relationships and cascade behavior
- Constraints and check rules
- Tenant isolation (mandatory filtering)
- Vector column and metadata persistence
- Soft delete behavior
- Index existence
"""
import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy import inspect, select

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
from app.repositories.ai_memory import AIMemoryRepository
from tests.factories import create_tenant, create_user


@pytest.mark.timeout(30)
class TestAIConversationModel:
    """Test AIConversation ORM model"""

    def test_create_conversation_minimal(self, db_session):
        """Create conversation with required fields only"""
        tenant = create_tenant(db_session)
        user = create_user(db_session, tenant_id=tenant.id)

        conversation = AIConversation(
            tenant_id=tenant.id,
            user_id=user.id,
            status="active",
        )
        db_session.add(conversation)
        db_session.commit()

        assert conversation.id is not None
        assert conversation.created_at is not None
        assert conversation.updated_at is not None
        assert conversation.tenant_id == tenant.id
        assert conversation.user_id == user.id
        assert conversation.deleted_at is None

    def test_conversation_with_metadata(self, db_session):
        """Create conversation with JSONB metadata"""
        tenant = create_tenant(db_session)

        metadata = {"source": "web_ui", "version": "v1", "tags": ["diagnostic"]}
        conversation = AIConversation(
            tenant_id=tenant.id,
            title="Test Conversation",
            metadata_json=metadata,
            status="active",
        )
        db_session.add(conversation)
        db_session.commit()
        db_session.refresh(conversation)

        assert conversation.metadata_json == metadata

    def test_conversation_cascade_delete_messages(self, db_session):
        """Deleting conversation cascades delete to messages"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)

        # Create conversation and message
        conv = repo.create_conversation(tenant.id, title="Test")
        msg = repo.append_message(
            tenant.id,
            conv.id,
            role="user",
            content="Hello",
            content_hash="abc123",
        )

        message_id = msg.id

        # Delete conversation
        db_session.delete(conv)
        db_session.commit()

        # Message should be deleted via cascade
        deleted_msg = db_session.get(AIMessage, message_id)
        assert deleted_msg is None

    def test_conversation_soft_delete_via_repository(self, db_session):
        """Repository soft-delete sets deleted_at"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)

        conv = repo.create_conversation(tenant.id, title="Test")
        conv_id = conv.id

        # Soft delete
        result = repo.soft_delete_conversation(tenant.id, conv_id)
        assert result is True

        # Query should exclude soft-deleted
        reloaded = repo.get_conversation(tenant.id, conv_id)
        assert reloaded is None

        # Raw query should show deleted_at set
        raw = db_session.query(AIConversation).filter(
            AIConversation.id == conv_id
        ).first()
        assert raw.deleted_at is not None


@pytest.mark.timeout(30)
class TestAIMessageModel:
    """Test AIMessage ORM model"""

    def test_create_message_with_content_hash(self, db_session):
        """Create message with content hash for deduplication"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)

        msg = repo.append_message(
            tenant.id,
            conv.id,
            role="assistant",
            content="Response text",
            content_hash="hash_abc123",
            token_count=42,
        )

        assert msg.content == "Response text"
        assert msg.content_hash == "hash_abc123"
        assert msg.role == "assistant"
        assert msg.token_count == 42

    def test_message_recorded_at_defaults_to_now(self, db_session):
        """Message recorded_at defaults to current time"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)

        before = datetime.utcnow()
        msg = repo.append_message(
            tenant.id,
            conv.id,
            role="user",
            content="Test",
            content_hash="hash",
        )
        after = datetime.utcnow()

        assert before <= msg.recorded_at <= after

    def test_message_with_metadata(self, db_session):
        """Message supports JSONB metadata"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)

        metadata = {"source": "api", "model": "gpt-4"}
        msg = repo.append_message(
            tenant.id,
            conv.id,
            role="system",
            content="System prompt",
            content_hash="hash",
            metadata=metadata,
        )

        assert msg.metadata_json == metadata

    def test_get_recent_messages_ordered(self, db_session):
        """get_recent_messages returns messages in reverse chronological order"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)

        # Create messages with delays
        msg1 = repo.append_message(
            tenant.id,
            conv.id,
            role="user",
            content="First",
            content_hash="hash1",
            recorded_at=datetime(2026, 5, 1, 10, 0, 0),
        )
        msg2 = repo.append_message(
            tenant.id,
            conv.id,
            role="assistant",
            content="Second",
            content_hash="hash2",
            recorded_at=datetime(2026, 5, 1, 10, 1, 0),
        )

        messages = repo.get_recent_messages(tenant.id, conv.id, limit=10)

        assert len(messages) == 2
        assert messages[0].id == msg2.id  # Most recent first
        assert messages[1].id == msg1.id


@pytest.mark.timeout(30)
class TestAIMemoryChunkModel:
    """Test AIMemoryChunk ORM model"""

    def test_create_chunk_from_message(self, db_session):
        """Create chunk derived from message"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)
        msg = repo.append_message(
            tenant.id,
            conv.id,
            role="user",
            content="Long message content here",
            content_hash="msg_hash",
        )

        chunk = repo.create_chunk(
            tenant.id,
            conv.id,
            chunk_text="Long message",
            chunk_hash="chunk_hash",
            chunk_index=0,
            chunk_type="message",
            message_id=msg.id,
        )

        assert chunk.message_id == msg.id
        assert chunk.summary_id is None
        assert chunk.chunk_text == "Long message"

    def test_create_chunk_from_summary(self, db_session):
        """Create chunk derived from summary"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)
        summary = repo.create_summary(
            tenant.id,
            conv.id,
            summary_text="Summary text",
            summary_hash="sum_hash",
        )

        chunk = repo.create_chunk(
            tenant.id,
            conv.id,
            chunk_text="Summary chunk",
            chunk_hash="chunk_hash",
            chunk_index=0,
            chunk_type="summary",
            summary_id=summary.id,
        )

        assert chunk.summary_id == summary.id
        assert chunk.message_id is None

    def test_chunk_check_constraint_requires_source(self, db_session):
        """Chunk must have message_id OR summary_id (not neither)"""
        tenant = create_tenant(db_session)
        conv = AIConversation(tenant_id=tenant.id, status="active")
        db_session.add(conv)
        db_session.commit()

        # Try to create chunk without source (violates CHECK constraint)
        chunk = AIMemoryChunk(
            tenant_id=tenant.id,
            conversation_id=conv.id,
            chunk_text="Text",
            chunk_hash="hash",
            chunk_index=0,
        )
        db_session.add(chunk)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_chunk_with_metadata(self, db_session):
        """Chunk supports JSONB metadata"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)
        msg = repo.append_message(
            tenant.id, conv.id, role="user", content="Test", content_hash="hash"
        )

        metadata = {"split_strategy": "recursive", "overlap": 20}
        chunk = repo.create_chunk(
            tenant.id,
            conv.id,
            chunk_text="Chunk",
            chunk_hash="hash",
            chunk_index=0,
            message_id=msg.id,
            metadata=metadata,
        )

        assert chunk.metadata_json == metadata


@pytest.mark.timeout(30)
class TestAIMemoryEmbeddingModel:
    """Test AIMemoryEmbedding ORM model"""

    def test_store_embedding_with_vector(self, db_session):
        """Store embedding vector in pgvector column"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)
        msg = repo.append_message(
            tenant.id, conv.id, role="user", content="Test", content_hash="hash"
        )
        chunk = repo.create_chunk(
            tenant.id,
            conv.id,
            chunk_text="Chunk",
            chunk_hash="chunk_hash",
            chunk_index=0,
            message_id=msg.id,
        )

        # Create embedding with 1536-dim vector
        embedding_vector = [0.1] * EMBEDDING_DIMENSION
        embedding = repo.store_embedding(
            tenant.id,
            chunk.id,
            embedding=embedding_vector,
            embedding_model="text-embedding-3-small",
            content_hash="chunk_hash",
        )

        assert len(embedding.embedding) == EMBEDDING_DIMENSION
        assert embedding.embedding_model == "text-embedding-3-small"
        assert embedding.embedding_dimension == EMBEDDING_DIMENSION

    def test_embedding_dimension_mismatch(self, db_session):
        """Embedding dimension validated"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)
        msg = repo.append_message(
            tenant.id, conv.id, role="user", content="Test", content_hash="hash"
        )
        chunk = repo.create_chunk(
            tenant.id,
            conv.id,
            chunk_text="Chunk",
            chunk_hash="chunk_hash",
            chunk_index=0,
            message_id=msg.id,
        )

        # Create embedding with wrong dimension
        wrong_vector = [0.1] * 768  # Wrong size
        embedding = repo.store_embedding(
            tenant.id,
            chunk.id,
            embedding=wrong_vector,
            embedding_model="text-embedding-2",
            content_hash="chunk_hash",
        )

        assert embedding.embedding_dimension == 768  # Stores actual dimension

    def test_embedding_with_metadata(self, db_session):
        """Embedding supports JSONB metadata"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)
        msg = repo.append_message(
            tenant.id, conv.id, role="user", content="Test", content_hash="hash"
        )
        chunk = repo.create_chunk(
            tenant.id,
            conv.id,
            chunk_text="Chunk",
            chunk_hash="chunk_hash",
            chunk_index=0,
            message_id=msg.id,
        )

        embedding_vector = [0.0] * EMBEDDING_DIMENSION
        metadata = {"inference_time_ms": 123, "api_call_id": "abc123"}
        embedding = repo.store_embedding(
            tenant.id,
            chunk.id,
            embedding=embedding_vector,
            embedding_model="test-model",
            content_hash="chunk_hash",
            metadata=metadata,
        )

        assert embedding.metadata_json == metadata


@pytest.mark.timeout(30)
class TestTenantIsolation:
    """Test mandatory tenant isolation in queries"""

    def test_conversation_query_respects_tenant(self, db_session):
        """get_conversation filters by tenant_id"""
        repo = AIMemoryRepository(db_session)
        tenant1 = create_tenant(db_session)
        tenant2 = create_tenant(db_session)

        conv1 = repo.create_conversation(tenant1.id, title="Tenant 1")
        conv2 = repo.create_conversation(tenant2.id, title="Tenant 2")

        # Tenant 1 cannot see Tenant 2's conversation
        result = repo.get_conversation(tenant1.id, conv2.id)
        assert result is None

        # Tenant 1 sees their own conversation
        result = repo.get_conversation(tenant1.id, conv1.id)
        assert result.id == conv1.id

    def test_messages_query_respects_tenant(self, db_session):
        """get_recent_messages filters by tenant_id"""
        repo = AIMemoryRepository(db_session)
        tenant1 = create_tenant(db_session)
        tenant2 = create_tenant(db_session)

        conv1 = repo.create_conversation(tenant1.id)
        conv2 = repo.create_conversation(tenant2.id)

        msg1 = repo.append_message(
            tenant1.id, conv1.id, role="user", content="T1", content_hash="hash1"
        )
        msg2 = repo.append_message(
            tenant2.id, conv2.id, role="user", content="T2", content_hash="hash2"
        )

        # Tenant 1 only sees their messages
        results = repo.get_recent_messages(tenant1.id, conv1.id)
        assert len(results) == 1
        assert results[0].id == msg1.id

        # Tenant 2 cannot see Tenant 1's messages
        results = repo.get_recent_messages(tenant1.id, conv2.id)
        assert len(results) == 0

    def test_chunk_query_respects_tenant(self, db_session):
        """get_chunk filters by tenant_id"""
        repo = AIMemoryRepository(db_session)
        tenant1 = create_tenant(db_session)
        tenant2 = create_tenant(db_session)

        conv1 = repo.create_conversation(tenant1.id)
        msg1 = repo.append_message(
            tenant1.id, conv1.id, role="user", content="Test", content_hash="hash"
        )
        chunk1 = repo.create_chunk(
            tenant1.id, conv1.id, chunk_text="C1", chunk_hash="ch1", chunk_index=0, message_id=msg1.id
        )

        # Tenant 2 cannot get Tenant 1's chunk
        result = repo.get_chunk(tenant2.id, chunk1.id)
        assert result is None

        # Tenant 1 can get their chunk
        result = repo.get_chunk(tenant1.id, chunk1.id)
        assert result.id == chunk1.id


@pytest.mark.timeout(30)
class TestSemanticSearch:
    """Test semantic search functionality"""

    def test_semantic_search_basic(self, db_session):
        """Semantic search returns chunks ranked by similarity"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)
        conv = repo.create_conversation(tenant.id)

        # Create chunks and embeddings
        msg = repo.append_message(
            tenant.id, conv.id, role="user", content="Test", content_hash="hash"
        )
        chunk = repo.create_chunk(
            tenant.id,
            conv.id,
            chunk_text="Semantic search example",
            chunk_hash="ch1",
            chunk_index=0,
            message_id=msg.id,
        )

        # Store embedding
        test_vector = [0.1] * EMBEDDING_DIMENSION
        repo.store_embedding(
            tenant.id,
            chunk.id,
            embedding=test_vector,
            embedding_model="test-model",
            content_hash="ch1",
        )

        # Search with similar vector
        results = repo.semantic_search(tenant.id, test_vector, limit=10)

        assert len(results) >= 1
        found_chunk, similarity = results[0]
        assert found_chunk.id == chunk.id
        assert 0.0 <= similarity <= 1.0

    def test_semantic_search_tenant_isolation(self, db_session):
        """Semantic search respects tenant_id filter"""
        repo = AIMemoryRepository(db_session)
        tenant1 = create_tenant(db_session)
        tenant2 = create_tenant(db_session)

        # Create chunks in different tenants
        conv1 = repo.create_conversation(tenant1.id)
        msg1 = repo.append_message(
            tenant1.id, conv1.id, role="user", content="Test", content_hash="hash"
        )
        chunk1 = repo.create_chunk(
            tenant1.id,
            conv1.id,
            chunk_text="Tenant 1 content",
            chunk_hash="ch1",
            chunk_index=0,
            message_id=msg1.id,
        )

        conv2 = repo.create_conversation(tenant2.id)
        msg2 = repo.append_message(
            tenant2.id, conv2.id, role="user", content="Test", content_hash="hash"
        )
        chunk2 = repo.create_chunk(
            tenant2.id,
            conv2.id,
            chunk_text="Tenant 2 content",
            chunk_hash="ch2",
            chunk_index=0,
            message_id=msg2.id,
        )

        # Store embeddings
        test_vector = [0.1] * EMBEDDING_DIMENSION
        repo.store_embedding(
            tenant1.id, chunk1.id, embedding=test_vector, embedding_model="test", content_hash="ch1"
        )
        repo.store_embedding(
            tenant2.id, chunk2.id, embedding=test_vector, embedding_model="test", content_hash="ch2"
        )

        # Tenant 1 search should only find Tenant 1 chunks
        results_t1 = repo.semantic_search(tenant1.id, test_vector, limit=10)
        assert len(results_t1) == 1
        assert results_t1[0][0].id == chunk1.id


@pytest.mark.timeout(30)
class TestSoftDelete:
    """Test soft delete behavior"""

    def test_soft_deleted_excluded_from_queries(self, db_session):
        """Soft-deleted records excluded from repository queries"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)

        conv = repo.create_conversation(tenant.id, title="To Delete")
        conv_id = conv.id

        # Soft delete
        repo.soft_delete_conversation(tenant.id, conv_id)

        # Query should not find it
        result = repo.get_conversation(tenant.id, conv_id)
        assert result is None

        # Raw query should show deleted_at set
        raw = db_session.query(AIConversation).filter(
            AIConversation.id == conv_id
        ).first()
        assert raw is not None
        assert raw.deleted_at is not None

    def test_soft_delete_idempotent(self, db_session):
        """Soft-deleting already-deleted record returns False"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)

        conv = repo.create_conversation(tenant.id)

        assert repo.soft_delete_conversation(tenant.id, conv.id) is True
        assert repo.soft_delete_conversation(tenant.id, conv.id) is False


@pytest.mark.timeout(30)
class TestIndexes:
    """Test that indexes exist on expected columns"""

    def test_conversation_indexes_exist(self, db_session):
        """Verify ai_conversations indexes"""
        inspector = inspect(db_session.bind)
        indexes = {idx['name'] for idx in inspector.get_indexes('ai_conversations')}

        expected = {
            'idx_ai_conversations_tenant_id',
            'idx_ai_conversations_user_id',
            'idx_ai_conversations_status',
            'idx_ai_conversations_tenant_created_at',
            'idx_ai_conversations_deleted_at',
        }
        assert expected.issubset(indexes)

    def test_message_indexes_exist(self, db_session):
        """Verify ai_messages indexes"""
        inspector = inspect(db_session.bind)
        indexes = {idx['name'] for idx in inspector.get_indexes('ai_messages')}

        expected = {
            'idx_ai_messages_tenant_conversation_recorded_at',
            'idx_ai_messages_content_hash',
            'idx_ai_messages_role',
            'idx_ai_messages_deleted_at',
        }
        assert expected.issubset(indexes)

    def test_chunk_indexes_exist(self, db_session):
        """Verify ai_memory_chunks indexes"""
        inspector = inspect(db_session.bind)
        indexes = {idx['name'] for idx in inspector.get_indexes('ai_memory_chunks')}

        expected = {
            'idx_ai_memory_chunks_tenant_conversation',
            'idx_ai_memory_chunks_chunk_hash',
            'idx_ai_memory_chunks_created_at',
            'idx_ai_memory_chunks_deleted_at',
        }
        assert expected.issubset(indexes)

    def test_embedding_indexes_exist(self, db_session):
        """Verify ai_memory_embeddings indexes"""
        inspector = inspect(db_session.bind)
        indexes = {idx['name'] for idx in inspector.get_indexes('ai_memory_embeddings')}

        expected = {
            'idx_ai_memory_embeddings_tenant_chunk',
            'idx_ai_memory_embeddings_model_version',
            'idx_ai_memory_embeddings_content_hash',
            'idx_ai_memory_embeddings_deleted_at',
            'idx_ai_memory_embeddings_vector_cosine',  # pgvector index
        }
        assert expected.issubset(indexes)

    def test_link_indexes_exist(self, db_session):
        """Verify ai_memory_links indexes"""
        inspector = inspect(db_session.bind)
        indexes = {idx['name'] for idx in inspector.get_indexes('ai_memory_links')}

        expected = {
            'idx_ai_memory_links_source',
            'idx_ai_memory_links_target',
            'idx_ai_memory_links_relation',
            'idx_ai_memory_links_deleted_at',
        }
        assert expected.issubset(indexes)
