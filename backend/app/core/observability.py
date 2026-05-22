from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import settings
from app.core.logging import request_id_ctx, trace_id_ctx, tenant_id_ctx, user_id_ctx

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def initialize_sentry() -> bool:
    if not settings.SENTRY_DSN:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENV,
            traces_sample_rate=settings.OTEL_TRACES_SAMPLE_RATIO,
            send_default_pii=False,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
        logger.info("sentry_initialized")
        return True
    except Exception:
        logger.exception("sentry_initialization_failed")
        return False


@lru_cache(maxsize=1)
def initialize_opentelemetry() -> bool:
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME, "deployment.environment": settings.ENV})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()
        logger.info("opentelemetry_initialized")
        return True
    except Exception:
        logger.exception("opentelemetry_initialization_failed")
        return False


def initialize_observability() -> None:
    initialize_sentry()
    initialize_opentelemetry()


def capture_exception(exc: Exception, *, request_path: str | None = None) -> None:
    try:
        import sentry_sdk

        sentry_sdk.set_context(
            "request",
            {
                "path": request_path,
                "request_id": request_id_ctx.get(),
                "trace_id": trace_id_ctx.get(),
                "tenant_id": tenant_id_ctx.get(),
                "user_id": user_id_ctx.get(),
            },
        )
        sentry_sdk.capture_exception(exc)
    except Exception:
        logger.exception("exception_monitoring_hook_failed")