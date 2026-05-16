import logging
import contextvars
import uuid
from typing import Optional

# Context var to hold request id per request
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


class SafeExtraFormatter(logging.Formatter):
    """Formatter that guarantees required structured fields exist on every record."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_ctx.get() or "-"
        if not hasattr(record, "service"):
            record.service = "-"
        return super().format(record)


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
    fmt = "%(asctime)s %(levelname)s %(service)s %(request_id)s %(name)s: %(message)s"
    filter_ = RequestIdFilter(service=service)

    root = logging.getLogger()
    root.setLevel(level)

    # Ensure existing handlers are safe with structured fields.
    for handler in root.handlers:
        handler.addFilter(filter_)
        current = handler.formatter
        if current is not None and hasattr(current, "_fmt") and "%(service)" in current._fmt:
            handler.setFormatter(SafeExtraFormatter(current._fmt, datefmt=current.datefmt))

    # Add one structured stream handler if none exists.
    if not any(getattr(h, "_cc_structured", False) for h in root.handlers):
        handler = logging.StreamHandler()
        handler._cc_structured = True
        handler.addFilter(filter_)
        handler.setFormatter(SafeExtraFormatter(fmt))
        root.addHandler(handler)


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
