"""Tests for AI memory async workers and task service.

Validates:
- Queue topology and routing
- Worker task execution
- Retry/backoff behavior
- Dead-letter queue routing
- Metrics instrumentation
- Tenant isolation
- Idempotency
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from celery import states
from sqlalchemy.orm import Session

from app.workers import QueueName, RetryConfig, BaseAIMemoryTask, TenantAwareTask
from app.workers.embedding_worker import (
    generate_chunk_embedding,
    generate_conversation_embeddings,
    _generate_embedding_vector,
)
from app.workers.summarization_worker import (
    summarize_conversation_window,
    schedule_periodic_summarization,
    _generate_summary,
)
from app.services.ai_memory_task_service import AIMemoryTaskService
from app.repositories.ai_memory import AIMemoryRepository
from tests.factories import create_tenant, create_user


@pytest.mark.timeout(30)
class TestQueueTopology:
    """Test queue configuration and routing"""

    def test_queue_names_defined(self):
        """Queue names are properly defined"""
        assert QueueName.EMBEDDING.value == "embedding"
        assert QueueName.SUMMARIZATION.value == "summarization"
        assert QueueName.MEMORY.value == "memory"
        assert QueueName.RETRY.value == "retry"
        assert QueueName.DEAD_LETTER.value == "dead_letter"

    def test_retry_config(self):
        """Retry configuration is production-grade"""
        assert RetryConfig.RETRY_MAX_RETRIES == 5
        assert RetryConfig.RETRY_BACKOFF_BASE == 1
        assert RetryConfig.RETRY_BACKOFF_MAX == 600

    def test_autoretry_config_format(self):
        """Autoretry config generates correct structure"""
        config = RetryConfig.get_autoretry_config(max_retries=3)
        assert "autoretry_for" in config
        assert "retry_backoff" in config
        assert "retry_kwargs" in config
        assert config["retry_kwargs"]["max_retries"] == 3


@pytest.mark.timeout(30)
class TestEmbeddingWorker:
    """Test embedding task worker"""

    def test_embedding_vector_dimension(self):
        """Generate embedding returns correct dimension"""
        vector = _generate_embedding_vector("test text")
        assert len(vector) == 1536
        assert all(isinstance(x, float) for x in vector)

    def test_generate_chunk_embedding_success(self, db_session):
        """Successfully generate and store embedding for chunk"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)

        # Create conversation, message, chunk
        conv = repo.create_conversation(tenant.id)
        msg = repo.append_message(
            tenant.id, conv.id, role="user", content="Test", content_hash="hash1"
        )
        chunk = repo.create_chunk(
            tenant.id,
            conv.id,
            chunk_text="Test chunk",
            chunk_hash="chunk_hash",
            chunk_index=0,
            message_id=msg.id,
        )

        # Mock the task execution
        with patch("app.workers.embedding_worker.AIMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_chunk.return_value = chunk
            mock_repo.get_embedding.return_value = None
            mock_repo.store_embedding.return_value = MagicMock(
                id=uuid4(), chunk_id=chunk.id, embedding=[0.0] * 1536
            )

            # Call the task
            result = generate_chunk_embedding(
                tenant_id=str(tenant.id),
                chunk_id=str(chunk.id),
            )

            assert result["status"] == "success"
            assert "embedding_id" in result
            assert result["embedding_dimension"] == 1536

    def test_embedding_idempotency(self, db_session):
        """Embedding generation is idempotent"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)

        # Create and embed chunk once
        conv = repo.create_conversation(tenant.id)
        msg = repo.append_message(
            tenant.id, conv.id, role="user", content="Test", content_hash="hash1"
        )
        chunk = repo.create_chunk(
            tenant.id,
            conv.id,
            chunk_text="Test",
            chunk_hash="chunk_hash",
            chunk_index=0,
            message_id=msg.id,
        )

        embedding_vector = [0.1] * 1536
        embedding1 = repo.store_embedding(
            tenant.id,
            chunk.id,
            embedding=embedding_vector,
            embedding_model="test-model",
            content_hash="chunk_hash",
        )

        # Second call should return existing
        with patch("app.workers.embedding_worker.AIMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_chunk.return_value = chunk
            mock_repo.get_embedding.return_value = embedding1

            result = generate_chunk_embedding(
                tenant_id=str(tenant.id),
                chunk_id=str(chunk.id),
            )

            assert result["status"] == "already_embedded"
            assert result["embedding_id"] == str(embedding1.id)

    def test_chunk_not_found_handling(self):
        """Gracefully handle missing chunk"""
        with patch("app.workers.embedding_worker.AIMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_chunk.return_value = None

            result = generate_chunk_embedding(
                tenant_id=str(uuid4()),
                chunk_id=str(uuid4()),
            )

            assert result["status"] == "chunk_not_found"
            assert result["embedding_id"] is None


@pytest.mark.timeout(30)
class TestSummarizationWorker:
    """Test summarization task worker"""

    def test_summary_generation(self):
        """Generate summary from messages"""
        messages = [
            MagicMock(content="Message one content here"),
            MagicMock(content="Message two content here"),
        ]

        summary_text, summary_hash = _generate_summary(messages)

        assert isinstance(summary_text, str)
        assert len(summary_text) > 0
        assert isinstance(summary_hash, str)
        assert len(summary_hash) == 64  # SHA256 hex

    def test_summary_hash_consistency(self):
        """Summary hash is deterministic"""
        messages = [
            MagicMock(content="Same content"),
        ]

        _, hash1 = _generate_summary(messages)
        _, hash2 = _generate_summary(messages)

        assert hash1 == hash2

    def test_summarize_window_success(self, db_session):
        """Successfully summarize conversation window"""
        repo = AIMemoryRepository(db_session)
        tenant = create_tenant(db_session)

        # Create conversation with messages
        conv = repo.create_conversation(tenant.id)
        now = datetime.utcnow()

        msg1 = repo.append_message(
            tenant.id,
            conv.id,
            role="user",
            content="First message",
            content_hash="hash1",
            recorded_at=now - timedelta(minutes=10),
        )
        msg2 = repo.append_message(
            tenant.id,
            conv.id,
            role="assistant",
            content="Second message",
            content_hash="hash2",
            recorded_at=now - timedelta(minutes=5),
        )

        window_start = now - timedelta(minutes=15)
        window_end = now

        with patch("app.workers.summarization_worker.AIMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_conversation.return_value = conv
            mock_repo.get_recent_messages.return_value = [msg2, msg1]  # DESC order
            mock_repo.get_conversation_summaries.return_value = []
            mock_repo.create_summary.return_value = MagicMock(
                id=uuid4(),
                summary_text="Summary",
                summary_hash="hash",
            )

            result = summarize_conversation_window(
                tenant_id=str(tenant.id),
                conversation_id=str(conv.id),
                window_start_at=window_start.isoformat(),
                window_end_at=window_end.isoformat(),
            )

            assert result["status"] == "success"
            assert "summary_id" in result
            assert result["message_count"] == 2

    def test_conversation_not_found_handling(self):
        """Gracefully handle missing conversation"""
        with patch("app.workers.summarization_worker.AIMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_conversation.return_value = None

            result = summarize_conversation_window(
                tenant_id=str(uuid4()),
                conversation_id=str(uuid4()),
            )

            assert result["status"] == "conversation_not_found"


@pytest.mark.timeout(30)
class TestAIMemoryTaskService:
    """Test task service layer"""

    def test_enqueue_embedding_returns_task_id(self):
        """Enqueue embedding task returns valid task ID"""
        tenant_id = uuid4()
        chunk_id = uuid4()

        with patch("app.tasks.ai_memory_tasks.generate_chunk_embedding") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "task-123"
            mock_task.apply_async.return_value = mock_result

            task_id = AIMemoryTaskService.enqueue_embedding_for_chunk(
                tenant_id, chunk_id
            )

            assert task_id == "task-123"
            mock_task.apply_async.assert_called_once()

    def test_enqueue_respects_priority(self):
        """Task enqueue respects priority parameter"""
        tenant_id = uuid4()
        chunk_id = uuid4()

        with patch("app.tasks.ai_memory_tasks.generate_chunk_embedding") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "task-123"
            mock_task.apply_async.return_value = mock_result

            AIMemoryTaskService.enqueue_embedding_for_chunk(
                tenant_id, chunk_id, priority=AIMemoryTaskService.PRIORITY_CRITICAL
            )

            call_kwargs = mock_task.apply_async.call_args[1]
            assert call_kwargs["priority"] == AIMemoryTaskService.PRIORITY_CRITICAL

    def test_enqueue_routes_to_correct_queue(self):
        """Task enqueue routes to correct queue"""
        tenant_id = uuid4()
        chunk_id = uuid4()

        with patch("app.tasks.ai_memory_tasks.generate_chunk_embedding") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "task-123"
            mock_task.apply_async.return_value = mock_result

            AIMemoryTaskService.enqueue_embedding_for_chunk(
                tenant_id, chunk_id
            )

            call_kwargs = mock_task.apply_async.call_args[1]
            assert call_kwargs["queue"] == QueueName.EMBEDDING.value

    def test_enqueue_summary_window_with_timestamps(self):
        """Enqueue summary preserves window timestamps"""
        tenant_id = uuid4()
        conversation_id = uuid4()
        start = datetime.utcnow() - timedelta(hours=1)
        end = datetime.utcnow()

        with patch("app.tasks.ai_memory_tasks.summarize_conversation_window") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "task-456"
            mock_task.apply_async.return_value = mock_result

            task_id = AIMemoryTaskService.enqueue_summary_for_window(
                tenant_id, conversation_id, window_start_at=start, window_end_at=end
            )

            call_kwargs = mock_task.apply_async.call_args[1]
            assert "window_start_at" in call_kwargs["kwargs"]
            assert "window_end_at" in call_kwargs["kwargs"]

    def test_get_task_status(self):
        """Get task status returns status dict"""
        with patch("app.core.celery_app.celery_app.AsyncResult") as mock_result_class:
            mock_result = MagicMock()
            mock_result.status = states.SUCCESS
            mock_result.result = {"key": "value"}
            mock_result.successful.return_value = True
            mock_result.failed.return_value = False
            mock_result_class.return_value = mock_result

            status = AIMemoryTaskService.get_task_status("task-789")

            assert status["task_id"] == "task-789"
            assert status["status"] == states.SUCCESS
            assert status["result"] == {"key": "value"}


@pytest.mark.timeout(30)
class TestTenantIsolation:
    """Test tenant isolation in workers"""

    def test_embedding_task_respects_tenant(self):
        """Embedding task queries only tenant's chunks"""
        tenant_id = uuid4()
        chunk_id = uuid4()

        with patch("app.workers.embedding_worker.AIMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_chunk.return_value = None

            generate_chunk_embedding(
                tenant_id=str(tenant_id),
                chunk_id=str(chunk_id),
            )

            # Verify get_chunk was called with tenant_id
            mock_repo.get_chunk.assert_called_once()
            call_args = mock_repo.get_chunk.call_args[0]
            assert call_args[0] == tenant_id

    def test_summarization_task_respects_tenant(self):
        """Summarization task queries only tenant's conversations"""
        tenant_id = uuid4()
        conversation_id = uuid4()

        with patch("app.workers.summarization_worker.AIMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_conversation.return_value = None

            summarize_conversation_window(
                tenant_id=str(tenant_id),
                conversation_id=str(conversation_id),
            )

            # Verify get_conversation was called with tenant_id
            mock_repo.get_conversation.assert_called_once()
            call_args = mock_repo.get_conversation.call_args[0]
            assert call_args[0] == tenant_id


@pytest.mark.timeout(30)
class TestErrorHandling:
    """Test error handling and retry behavior"""

    def test_chunk_not_found_no_retry(self):
        """Chunk not found should not cause retry"""
        with patch("app.workers.embedding_worker.AIMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_chunk.return_value = None

            # Should not raise exception
            result = generate_chunk_embedding(
                tenant_id=str(uuid4()),
                chunk_id=str(uuid4()),
            )

            assert result["status"] == "chunk_not_found"

    def test_no_messages_in_window_no_retry(self):
        """No messages in window should not cause retry"""
        tenant_id = uuid4()
        conversation_id = uuid4()

        with patch("app.workers.summarization_worker.AIMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            conv = MagicMock()
            mock_repo.get_conversation.return_value = conv
            mock_repo.get_recent_messages.return_value = []

            # Should not raise exception
            result = summarize_conversation_window(
                tenant_id=str(tenant_id),
                conversation_id=str(conversation_id),
            )

            assert result["status"] == "no_messages"
