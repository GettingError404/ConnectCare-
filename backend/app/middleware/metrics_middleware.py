from __future__ import annotations

import time
import logging
from typing import Callable

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core import metrics

logger = logging.getLogger(__name__)


class MetricsMiddleware:
    """FastAPI/Starlette middleware that records request counts and latencies.

    - Non-blocking: uses in-process prometheus_client calls (thread-safe)
    - Uses route.path template when available to avoid path cardinality
    - Adds tenant label from request.state.tenant_id (best-effort)
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        start = time.perf_counter()
        tenant = getattr(request.state, "tenant_id", None)
        method = request.method
        route = "unknown"
        try:
            route_obj = scope.get("route")
            if route_obj and getattr(route_obj, "path", None):
                route = route_obj.path
            else:
                route = scope.get("path", request.url.path)
        except Exception:
            route = request.url.path

        async def _send_wrapper(message):
            # intercept response start to capture status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration = time.perf_counter() - start
                try:
                    metrics.inc_http_request(method=method, endpoint=route, status_code=str(status_code), tenant=str(tenant) if tenant else "-")
                    metrics.observe_http_request_latency(method=method, endpoint=route, duration=duration, tenant=str(tenant) if tenant else "-")
                except Exception:
                    logger.exception("Failed to record request metrics")
            await send(message)

        await self.app(scope, receive, _send_wrapper)


__all__ = ["MetricsMiddleware"]
