"""Prometheus metrics registry and helpers.

Provides a singleton registry that is multiprocess-aware when `prometheus_multiproc_dir`
or `PROMETHEUS_MULTIPROC_DIR` is set (standard for gunicorn/uvicorn workers).

Expose helper metrics objects and a `metrics_app()`-style collector for `/metrics`.
"""
from __future__ import annotations

import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    from prometheus_client import multiprocess as prom_multiproc
    MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR") or os.getenv("prometheus_multiproc_dir")
except Exception:
    # prometheus_client not installed — define no-op shims to avoid hard failures
    CollectorRegistry = None  # type: ignore
    Counter = None  # type: ignore
    Histogram = None  # type: ignore
    Gauge = None  # type: ignore
    generate_latest = lambda registry=None: b""  # type: ignore
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    prom_multiproc = None
    MULTIPROC_DIR = None


# Singleton registry and metric objects
_registry = None
_metrics_inited = False


def get_registry():
    global _registry
    if _registry is not None:
        return _registry

    if CollectorRegistry is None:
        return None

    if MULTIPROC_DIR:
        # In multiprocess mode we use a fresh CollectorRegistry and register the
        # multiprocess collector which will aggregate metrics from worker files.
        _registry = CollectorRegistry()
        try:
            prom_multiproc.MultiProcessCollector(_registry)
        except Exception as exc:
            logger.exception("Failed to initialize MultiProcessCollector: %s", exc)
    else:
        _registry = CollectorRegistry()
    return _registry


# Metrics namespace: create lazily once
_http_requests_total = None
_http_request_latency = None
_mqtt_messages_total = None
_mqtt_publish_failures = None
_ingest_total = None
_ingest_duplicates_total = None
_alerts_triggered_total = None
_alerts_cooldown_skipped_total = None
_ws_active_connections = None
_ws_broadcasts_total = None
_celery_task_duration = None
_celery_task_failures = None
_celery_task_success = None
_celery_task_retries = None
_redis_eventbus_publishes = None
_ai_memory_embeddings_generated = None
_ai_memory_embeddings_failed = None
_ai_memory_summaries_generated = None
_ai_memory_summaries_failed = None
_ai_memory_chunks_created = None
_ai_memory_searches = None
_embedding_generation_latency = None
_embedding_provider_failures = None
_embedding_requests_total = None
_embedding_cache_hits = None
_ai_memory_ingestions = None
_ai_memory_retrieval_latency = None
_ai_memory_retrieval_requests = None


def _init_metrics():
    global _metrics_inited
    global _http_requests_total, _http_request_latency
    global _mqtt_messages_total, _mqtt_publish_failures
    global _ingest_total, _ingest_duplicates_total
    global _alerts_triggered_total, _alerts_cooldown_skipped_total
    global _ws_active_connections, _ws_broadcasts_total
    global _celery_task_duration, _celery_task_failures, _celery_task_success, _celery_task_retries
    global _redis_eventbus_publishes
    global _ai_memory_embeddings_generated, _ai_memory_embeddings_failed
    global _ai_memory_summaries_generated, _ai_memory_summaries_failed
    global _ai_memory_chunks_created, _ai_memory_searches
    global _embedding_generation_latency, _embedding_provider_failures
    global _embedding_requests_total, _embedding_cache_hits
    global _ai_memory_ingestions, _ai_memory_retrieval_latency, _ai_memory_retrieval_requests

    if _metrics_inited:
        return

    registry = get_registry()
    if registry is None:
        logger.warning("prometheus_client not available — metrics disabled")
        _metrics_inited = True
        return

    # HTTP metrics: keep labels low-cardinality; endpoint is the route path template
    _http_requests_total = Counter(
        "cc_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code", "tenant"],
        registry=registry,
    )

    _http_request_latency = Histogram(
        "cc_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint", "tenant"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        registry=registry,
    )

    # MQTT metrics
    _mqtt_messages_total = Counter(
        "cc_mqtt_messages_total",
        "MQTT messages processed",
        ["result", "tenant"],
        registry=registry,
    )
    _mqtt_publish_failures = Counter(
        "cc_mqtt_publish_failures_total",
        "MQTT publish failures",
        ["tenant"],
        registry=registry,
    )

    # ingestion
    _ingest_total = Counter(
        "cc_ingest_events_total",
        "Total ingest events processed",
        ["result", "tenant"],
        registry=registry,
    )
    _ingest_duplicates_total = Counter(
        "cc_ingest_duplicates_total",
        "Ingest duplicate events",
        ["tenant"],
        registry=registry,
    )

    # alerts
    _alerts_triggered_total = Counter(
        "cc_alerts_triggered_total",
        "Alerts triggered",
        ["severity", "tenant"],
        registry=registry,
    )
    _alerts_cooldown_skipped_total = Counter(
        "cc_alerts_cooldown_skipped_total",
        "Alerts skipped due to cooldown",
        ["tenant"],
        registry=registry,
    )

    # websocket
    _ws_active_connections = Gauge(
        "cc_ws_active_connections",
        "Active websocket connections",
        ["tenant"],
        registry=registry,
    )
    _ws_broadcasts_total = Counter(
        "cc_ws_broadcasts_total",
        "Websocket broadcasts",
        ["tenant"],
        registry=registry,
    )

    # celery
    _celery_task_duration = Histogram(
        "cc_celery_task_duration_seconds",
        "Celery task duration seconds",
        ["task_name"],
        buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0),
        registry=registry,
    )
    _celery_task_failures = Counter(
        "cc_celery_task_failures_total",
        "Celery task failures",
        ["task_name"],
        registry=registry,
    )
    _celery_task_success = Counter(
        "cc_celery_task_success_total",
        "Celery task successes",
        ["task_name"],
        registry=registry,
    )
    _celery_task_retries = Counter(
        "cc_celery_task_retries_total",
        "Celery task retries",
        ["task_name"],
        registry=registry,
    )

    # redis/eventbus
    _redis_eventbus_publishes = Counter(
        "cc_eventbus_publishes_total",
        "EventBus publishes to Redis",
        ["channel", "status"],
        registry=registry,
    )

    # AI memory metrics
    _ai_memory_embeddings_generated = Counter(
        "cc_ai_memory_embeddings_generated_total",
        "AI memory embeddings generated",
        ["embedding_model"],
        registry=registry,
    )
    _ai_memory_embeddings_failed = Counter(
        "cc_ai_memory_embeddings_failed_total",
        "AI memory embedding generation failures",
        ["embedding_model"],
        registry=registry,
    )
    _ai_memory_summaries_generated = Counter(
        "cc_ai_memory_summaries_generated_total",
        "AI memory summaries generated",
        registry=registry,
    )
    _ai_memory_summaries_failed = Counter(
        "cc_ai_memory_summaries_failed_total",
        "AI memory summary generation failures",
        registry=registry,
    )
    _ai_memory_chunks_created = Counter(
        "cc_ai_memory_chunks_created_total",
        "AI memory chunks created",
        ["chunk_type"],
        registry=registry,
    )
    _ai_memory_searches = Counter(
        "cc_ai_memory_searches_total",
        "AI memory semantic searches executed",
        ["tenant"],
        registry=registry,
    )

    _embedding_generation_latency = Histogram(
        "cc_embedding_generation_duration_seconds",
        "Embedding generation duration in seconds",
        ["provider", "model"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
        registry=registry,
    )
    _embedding_provider_failures = Counter(
        "cc_embedding_provider_failures_total",
        "Embedding provider failures",
        ["provider", "model"],
        registry=registry,
    )
    _embedding_requests_total = Counter(
        "cc_embedding_requests_total",
        "Embedding requests by status",
        ["provider", "model", "status"],
        registry=registry,
    )
    _embedding_cache_hits = Counter(
        "cc_embedding_cache_hits_total",
        "Embedding cache hits",
        ["provider", "model"],
        registry=registry,
    )

    _ai_memory_ingestions = Counter(
        "cc_ai_memory_ingestions_total",
        "AI memory ingestions",
        ["source_type", "status"],
        registry=registry,
    )

    _ai_memory_retrieval_latency = Histogram(
        "cc_ai_memory_retrieval_duration_seconds",
        "AI memory retrieval duration",
        ["mode"],
        buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
        registry=registry,
    )

    _ai_memory_retrieval_requests = Counter(
        "cc_ai_memory_retrieval_requests_total",
        "AI memory retrieval requests",
        ["mode", "status"],
        registry=registry,
    )

    _metrics_inited = True


def inc_http_request(method: str, endpoint: str, status_code: str, tenant: Optional[str] = "-"):
    _init_metrics()
    if _http_requests_total is None:
        return
    try:
        _http_requests_total.labels(method=method, endpoint=endpoint, status_code=str(status_code), tenant=tenant or "-").inc()
    except Exception:
        logger.exception("Failed to increment http_requests_total")


def observe_http_request_latency(method: str, endpoint: str, duration: float, tenant: Optional[str] = "-"):
    _init_metrics()
    if _http_request_latency is None:
        return
    try:
        _http_request_latency.labels(method=method, endpoint=endpoint, tenant=tenant or "-").observe(duration)
    except Exception:
        logger.exception("Failed to observe http_request_latency")


def inc_mqtt_message(result: str, tenant: Optional[str] = "-"):
    _init_metrics()
    if _mqtt_messages_total is None:
        return
    try:
        _mqtt_messages_total.labels(result=result, tenant=tenant or "-").inc()
    except Exception:
        logger.exception("Failed to inc mqtt_messages_total")


def inc_mqtt_publish_failure(tenant: Optional[str] = "-"):
    _init_metrics()
    if _mqtt_publish_failures is None:
        return
    try:
        _mqtt_publish_failures.labels(tenant=tenant or "-").inc()
    except Exception:
        logger.exception("Failed to inc mqtt_publish_failures")


def inc_ingest(result: str, tenant: Optional[str] = "-"):
    _init_metrics()
    if _ingest_total is None:
        return
    try:
        _ingest_total.labels(result=result, tenant=tenant or "-").inc()
    except Exception:
        logger.exception("Failed to inc ingest_total")


def inc_ingest_duplicate(tenant: Optional[str] = "-"):
    _init_metrics()
    if _ingest_duplicates_total is None:
        return
    try:
        _ingest_duplicates_total.labels(tenant=tenant or "-").inc()
    except Exception:
        logger.exception("Failed to inc ingest_duplicates")


def inc_alert_triggered(severity: str, tenant: Optional[str] = "-"):
    _init_metrics()
    if _alerts_triggered_total is None:
        return
    try:
        _alerts_triggered_total.labels(severity=severity or "unknown", tenant=tenant or "-").inc()
    except Exception:
        logger.exception("Failed to inc alerts_triggered")


def inc_alert_cooldown_skipped(tenant: Optional[str] = "-"):
    _init_metrics()
    if _alerts_cooldown_skipped_total is None:
        return
    try:
        _alerts_cooldown_skipped_total.labels(tenant=tenant or "-").inc()
    except Exception:
        logger.exception("Failed to inc alerts_cooldown_skipped")


def ws_connection_inc(tenant: Optional[str] = "-"):
    _init_metrics()
    if _ws_active_connections is None:
        return
    try:
        _ws_active_connections.labels(tenant=tenant or "-").inc()
    except Exception:
        logger.exception("Failed to inc ws active connections")


def ws_connection_dec(tenant: Optional[str] = "-"):
    _init_metrics()
    if _ws_active_connections is None:
        return
    try:
        _ws_active_connections.labels(tenant=tenant or "-").dec()
    except Exception:
        logger.exception("Failed to dec ws active connections")


def inc_ws_broadcast(tenant: Optional[str] = "-"):
    _init_metrics()
    if _ws_broadcasts_total is None:
        return
    try:
        _ws_broadcasts_total.labels(tenant=tenant or "-").inc()
    except Exception:
        logger.exception("Failed to inc ws_broadcasts")


def observe_celery_task_duration(task_name: str, duration: float):
    _init_metrics()
    if _celery_task_duration is None:
        return
    try:
        _celery_task_duration.labels(task_name=task_name).observe(duration)
    except Exception:
        logger.exception("Failed to observe celery task duration")


def inc_celery_task_failure(task_name: str):
    _init_metrics()
    if _celery_task_failures is None:
        return
    try:
        _celery_task_failures.labels(task_name=task_name).inc()
    except Exception:
        logger.exception("Failed to inc celery task failure")


def inc_celery_task_success(task_name: str):
    _init_metrics()
    if _celery_task_success is None:
        return
    try:
        _celery_task_success.labels(task_name=task_name).inc()
    except Exception:
        logger.exception("Failed to inc celery task success")


def inc_celery_task_retry(task_name: str):
    _init_metrics()
    if _celery_task_retries is None:
        return
    try:
        _celery_task_retries.labels(task_name=task_name).inc()
    except Exception:
        logger.exception("Failed to inc celery task retry")


def inc_eventbus_publish(channel: str, status: str):
    _init_metrics()
    if _redis_eventbus_publishes is None:
        return
    try:
        _redis_eventbus_publishes.labels(channel=channel, status=status).inc()
    except Exception:
        logger.exception("Failed to inc eventbus publish metric")


def inc_ai_memory_embeddings_generated(embedding_model: str):
    _init_metrics()
    if _ai_memory_embeddings_generated is None:
        return
    try:
        _ai_memory_embeddings_generated.labels(embedding_model=embedding_model).inc()
    except Exception:
        logger.exception("Failed to inc ai_memory embeddings generated")


def inc_ai_memory_embeddings_failed(embedding_model: str):
    _init_metrics()
    if _ai_memory_embeddings_failed is None:
        return
    try:
        _ai_memory_embeddings_failed.labels(embedding_model=embedding_model).inc()
    except Exception:
        logger.exception("Failed to inc ai_memory embeddings failed")


def inc_ai_memory_summaries_generated():
    _init_metrics()
    if _ai_memory_summaries_generated is None:
        return
    try:
        _ai_memory_summaries_generated.inc()
    except Exception:
        logger.exception("Failed to inc ai_memory summaries generated")


def inc_ai_memory_summaries_failed():
    _init_metrics()
    if _ai_memory_summaries_failed is None:
        return
    try:
        _ai_memory_summaries_failed.inc()
    except Exception:
        logger.exception("Failed to inc ai_memory summaries failed")


def inc_ai_memory_chunks_created(chunk_type: str = "message"):
    _init_metrics()
    if _ai_memory_chunks_created is None:
        return
    try:
        _ai_memory_chunks_created.labels(chunk_type=chunk_type).inc()
    except Exception:
        logger.exception("Failed to inc ai_memory chunks created")


def inc_ai_memory_searches(tenant: str = "-"):
    _init_metrics()
    if _ai_memory_searches is None:
        return
    try:
        _ai_memory_searches.labels(tenant=tenant).inc()
    except Exception:
        logger.exception("Failed to inc ai_memory searches")


def observe_embedding_generation_latency(provider: str, model: str, duration: float):
    _init_metrics()
    if _embedding_generation_latency is None:
        return
    try:
        _embedding_generation_latency.labels(provider=provider, model=model).observe(duration)
    except Exception:
        logger.exception("Failed to observe embedding generation latency")


def inc_embedding_provider_failures(provider: str, model: str):
    _init_metrics()
    if _embedding_provider_failures is None:
        return
    try:
        _embedding_provider_failures.labels(provider=provider, model=model).inc()
    except Exception:
        logger.exception("Failed to increment embedding provider failures")


def inc_embedding_requests(provider: str, model: str, status: str):
    _init_metrics()
    if _embedding_requests_total is None:
        return
    try:
        _embedding_requests_total.labels(provider=provider, model=model, status=status).inc()
    except Exception:
        logger.exception("Failed to increment embedding requests")


def inc_embedding_cache_hits(provider: str, model: str):
    _init_metrics()
    if _embedding_cache_hits is None:
        return
    try:
        _embedding_cache_hits.labels(provider=provider, model=model).inc()
    except Exception:
        logger.exception("Failed to increment embedding cache hits")


def inc_ai_memory_ingestions(source_type: str, status: str):
    _init_metrics()
    if _ai_memory_ingestions is None:
        return
    try:
        _ai_memory_ingestions.labels(source_type=source_type, status=status).inc()
    except Exception:
        logger.exception("Failed to increment ai_memory ingestions")


def observe_ai_memory_retrieval_latency(mode: str, duration: float):
    _init_metrics()
    if _ai_memory_retrieval_latency is None:
        return
    try:
        _ai_memory_retrieval_latency.labels(mode=mode).observe(duration)
    except Exception:
        logger.exception("Failed to observe ai_memory retrieval latency")


def inc_ai_memory_retrieval_requests(mode: str, status: str):
    _init_metrics()
    if _ai_memory_retrieval_requests is None:
        return
    try:
        _ai_memory_retrieval_requests.labels(mode=mode, status=status).inc()
    except Exception:
        logger.exception("Failed to increment ai_memory retrieval requests")


def generate_latest_metrics() -> bytes:
    registry = get_registry()
    try:
        if registry is None:
            return b""
        return generate_latest(registry)
    except Exception:
        logger.exception("Failed to generate latest metrics")
        return b""


__all__ = [
    "get_registry",
    "inc_http_request",
    "observe_http_request_latency",
    "inc_mqtt_message",
    "inc_mqtt_publish_failure",
    "inc_ingest",
    "inc_ingest_duplicate",
    "inc_alert_triggered",
    "inc_alert_cooldown_skipped",
    "ws_connection_inc",
    "ws_connection_dec",
    "inc_ws_broadcast",
    "observe_celery_task_duration",
    "inc_celery_task_failure",
    "inc_celery_task_success",
    "inc_celery_task_retry",
    "inc_ai_memory_embeddings_generated",
    "inc_ai_memory_embeddings_failed",
    "inc_ai_memory_summaries_generated",
    "inc_ai_memory_summaries_failed",
    "inc_ai_memory_chunks_created",
    "inc_ai_memory_searches",
    "observe_embedding_generation_latency",
    "inc_embedding_provider_failures",
    "inc_embedding_requests",
    "inc_embedding_cache_hits",
    "inc_ai_memory_ingestions",
    "observe_ai_memory_retrieval_latency",
    "inc_ai_memory_retrieval_requests",
    "inc_eventbus_publish",
    "generate_latest_metrics",
    "CONTENT_TYPE_LATEST",
]
