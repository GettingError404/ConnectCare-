import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable

from app.core.logging import get_logger, set_request_id, clear_request_id, trace_id_ctx


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger_name: str = "app"):
        super().__init__(app)
        self.logger = get_logger(logger_name)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # pick up incoming request id or generate new
        incoming = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
        request_id = incoming or str(uuid.uuid4())
        token = set_request_id(request_id)
        incoming_trace = request.headers.get("X-Trace-ID") or request.headers.get("x-trace-id")
        trace_id = incoming_trace or request_id
        trace_token = trace_id_ctx.set(trace_id)

        start = time.time()
        try:
            response = await call_next(request)
        except Exception:
            # exception handlers will log; re-raise so FastAPI can handle
            raise
        finally:
            duration_ms = int((time.time() - start) * 1000)
            status_code = getattr(locals().get('response', None), 'status_code', None)
            # Build a safe status code value
            if status_code is None:
                try:
                    # if response not in locals (exception path), default to 500
                    status_code = 500
                except Exception:
                    status_code = 0

            self.logger.info(
                "request_complete",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": duration_ms,
                },
            )
            # attach request id header
            try:
                response.headers.setdefault("X-Request-ID", request_id)
                response.headers.setdefault("X-Trace-ID", trace_id)
            except Exception:
                # response may not be defined in error paths
                pass
            clear_request_id(token)
            trace_id_ctx.reset(trace_token)

        return response
