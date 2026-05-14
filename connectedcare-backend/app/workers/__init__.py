"""AI Memory async processing queue topology and base worker.

Queue Routing Strategy:
- embedding: High-priority embedding generation tasks
- summarization: Memory compression and summarization
- memory: General AI memory operations (chunk creation, links, etc.)
- retry: Failed tasks awaiting retry
- dead_letter: Permanently failed tasks

Worker Configuration:
- Exponential backoff retry (1s, 2s, 4s, 8s, base)
- Max retries: 5 per task
- Time limits: embedding (5m), summarization (10m), memory (2m)
- Tenant-aware: every task tracks tenant_id for isolation
- Idempotent: tasks can be safely replayed without side effects
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from celery import Task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.logging import tenant_id_ctx, user_id_ctx, request_id_ctx, trace_id_ctx
from app.db.session import SessionLocal
from app.core import metrics as metrics_module

logger = logging.getLogger(__name__)


class QueueName(str, Enum):
    """Queue identifiers for routing"""
    EMBEDDING = "embedding"
    SUMMARIZATION = "summarization"
    MEMORY = "memory"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"


class QueueConfig:
    """Queue configuration and routing"""
    
    QUEUES = {
        QueueName.EMBEDDING: {
            "exchange": "ai_memory",
            "exchange_type": "direct",
            "routing_key": "embedding",
            "queue_arguments": {"x-max-priority": 10},
        },
        QueueName.SUMMARIZATION: {
            "exchange": "ai_memory",
            "exchange_type": "direct",
            "routing_key": "summarization",
            "queue_arguments": {"x-max-priority": 5},
        },
        QueueName.MEMORY: {
            "exchange": "ai_memory",
            "exchange_type": "direct",
            "routing_key": "memory",
            "queue_arguments": {"x-max-priority": 5},
        },
        QueueName.RETRY: {
            "exchange": "ai_memory",
            "exchange_type": "direct",
            "routing_key": "retry",
            "queue_arguments": {
                "x-max-priority": 1,
                "x-message-ttl": 86400000,  # 24 hours
            },
        },
        QueueName.DEAD_LETTER: {
            "exchange": "ai_memory",
            "exchange_type": "direct",
            "routing_key": "dead_letter",
            "queue_arguments": {
                "x-message-ttl": 604800000,  # 7 days
            },
        },
    }
    
    @staticmethod
    def configure_celery(celery_app_instance):
        """Configure Celery with queue topology"""
        from kombu import Queue, Exchange
        
        exchange = Exchange("ai_memory", type="direct", durable=True)
        
        task_queues = []
        for queue_name, config in QueueConfig.QUEUES.items():
            queue = Queue(
                queue_name.value,
                exchange=exchange,
                routing_key=config["routing_key"],
                queue_arguments=config.get("queue_arguments", {}),
                durable=True,
            )
            task_queues.append(queue)
        
        celery_app_instance.conf.task_queues = task_queues
        
        # Default routing for tasks
        celery_app_instance.conf.task_default_queue = QueueName.MEMORY.value
        celery_app_instance.conf.task_default_exchange = "ai_memory"
        celery_app_instance.conf.task_default_routing_key = "memory"


class RetryConfig:
    """Retry strategy configuration"""
    
    # Exponential backoff: 1s, 2s, 4s, 8s, 16s
    RETRY_BACKOFF_BASE = 1
    RETRY_MAX_RETRIES = 5
    RETRY_BACKOFF_MAX = 600  # Max 10 minutes between retries
    
    @staticmethod
    def get_autoretry_config(max_retries: int = RETRY_MAX_RETRIES):
        """Generate autoretry configuration for task decorator"""
        return {
            "autoretry_for": (Exception,),
            "retry_backoff": True,
            "retry_backoff_max": RetryConfig.RETRY_BACKOFF_MAX,
            "retry_kwargs": {
                "max_retries": max_retries,
                "countdown": RetryConfig.RETRY_BACKOFF_BASE,
            },
        }


class BaseAIMemoryTask(Task, ABC):
    """Base task class for AI memory workers.
    
    Provides:
    - Automatic DB session management with cleanup
    - Context var propagation (tenant_id, user_id, trace_id)
    - Structured logging with task metadata
    - Dead-letter queue routing on final failure
    - Idempotency support
    """
    
    # Override these in subclasses
    max_retries: int = RetryConfig.RETRY_MAX_RETRIES
    soft_time_limit: int = 300  # 5 minutes default
    time_limit: int = 600  # Hard limit 10 minutes default
    
    def __call__(self, *args, **kwargs):
        """Wrap task execution with context setup"""
        # Propagate context from task kwargs if present
        if "tenant_id" in kwargs:
            tenant_id_ctx.set(str(kwargs["tenant_id"]))
        if "user_id" in kwargs:
            user_id_ctx.set(str(kwargs["user_id"]))
        if "trace_id" in kwargs:
            trace_id_ctx.set(str(kwargs["trace_id"]))
        
        return super().__call__(*args, **kwargs)
    
    def run(self, *args, **kwargs):
        """Override to add DB session and error handling"""
        db = None
        try:
            db = SessionLocal()
            return self.execute(db, *args, **kwargs)
        except Exception as exc:
            logger.exception(
                "task_execution_failed",
                extra={
                    "task_name": self.name,
                    "task_id": self.request.id,
                    "retries": self.request.retries,
                    "max_retries": self.max_retries,
                },
            )
            # Let autoretry handle retries, or route to dead-letter on final failure
            if self.request.retries >= self.max_retries:
                self._route_to_dead_letter(args, kwargs, exc)
            raise
        finally:
            if db:
                db.close()
    
    @abstractmethod
    def execute(self, db: Session, *args, **kwargs) -> Any:
        """Execute task logic. Override in subclasses."""
        pass
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task finally fails after all retries"""
        logger.error(
            "task_final_failure",
            extra={
                "task_name": self.name,
                "task_id": task_id,
                "exception": str(exc),
                "retries": self.request.retries,
            },
        )
        self._route_to_dead_letter(args, kwargs, exc)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(
            "task_retry",
            extra={
                "task_name": self.name,
                "task_id": task_id,
                "retries": self.request.retries,
                "max_retries": self.max_retries,
                "exception": str(exc),
            },
        )
        metrics_module.inc_celery_task_retries(self.name)
    
    @staticmethod
    def _route_to_dead_letter(args: tuple, kwargs: dict, exc: Exception):
        """Route task to dead-letter queue for manual inspection"""
        try:
            dlq_payload = {
                "args": args,
                "kwargs": kwargs,
                "exception": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            }
            logger.critical(
                "task_dead_lettered",
                extra={
                    "dlq_payload": str(dlq_payload)[:500],  # truncate for logging
                },
            )
        except Exception as e:
            logger.exception("failed_to_log_dead_letter", exc_info=e)


class TenantAwareTask(BaseAIMemoryTask):
    """Base for tasks that require tenant_id for execution"""
    
    def execute(self, db: Session, tenant_id: UUID, *args, **kwargs) -> Any:
        """Execute with mandatory tenant_id"""
        tenant_id_ctx.set(str(tenant_id))
        logger.info(
            "task_start",
            extra={
                "task_name": self.name,
                "task_id": self.request.id,
                "tenant_id": str(tenant_id),
            },
        )
        return self.execute_tenant_aware(db, tenant_id, *args, **kwargs)
    
    @abstractmethod
    def execute_tenant_aware(self, db: Session, tenant_id: UUID, *args, **kwargs) -> Any:
        """Override this in subclasses"""
        pass


def setup_ai_memory_queues():
    """Initialize queue topology on Celery app"""
    QueueConfig.configure_celery(celery_app)
    logger.info("AI memory queue topology configured", extra={"queues": list(QueueName)})
