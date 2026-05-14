import logging
import contextvars
import uuid
from typing import Optional

# Context var to hold request id per request
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        record.service = self.service
        return True


def configure_logging(level: int = logging.INFO, service: str = "connectedcare-backend") -> None:
    """Configure root logger with structured-ish formatter and request_id support."""
    handler = logging.StreamHandler()
    fmt = "%(asctime)s %(levelname)s %(service)s %(request_id)s %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers in hot-reload/dev
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)

    # Add request id filter so every log record has request_id and service
    root.addFilter(RequestIdFilter(service=service))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_request_id(request_id: Optional[str] = None) -> contextvars.Token:
    """Set request id in the current context. Returns token for reset."""
    if not request_id:
        request_id = str(uuid.uuid4())
    return request_id_ctx.set(request_id)


def clear_request_id(token: contextvars.Token) -> None:
    request_id_ctx.reset(token)


__all__ = [
    "configure_logging",
    "get_logger",
    "set_request_id",
    "clear_request_id",
    "request_id_ctx",
]
