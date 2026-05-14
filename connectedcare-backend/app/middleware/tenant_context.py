"""
Tenant context middleware for multi-tenant request isolation.

Extracts tenant_id from JWT token and injects it into request.state
for use by services and repositories throughout the request lifecycle.
"""

from typing import Callable
from uuid import UUID
import logging
from jose import jwt, JWTError

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import settings

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts tenant_id from JWT and sets request context.

    Assumes JWT token contains 'tenant_id' claim. If missing or invalid,
    request proceeds but tenant_id remains None for public endpoints.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract tenant_id from JWT and set in request.state."""
        tenant_id = None

        # Try to extract tenant_id from JWT token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=[settings.ALGORITHM],
                )
                tenant_id = payload.get("tenant_id")
                if tenant_id:
                    tenant_id = UUID(tenant_id)
            except (JWTError, ValueError):
                # Invalid token or missing tenant_id - proceed without it
                pass

        # Set tenant context in request state
        request.state.tenant_id = tenant_id

        # Log tenant context for debugging
        if tenant_id:
            logger.debug(
                "tenant_context_set",
                extra={
                    "tenant_id": str(tenant_id),
                    "path": request.url.path,
                    "method": request.method,
                },
            )

        response = await call_next(request)
        return response


def get_tenant_id_from_request(request: Request) -> UUID | None:
    """Extract tenant_id from request context.

    Utility function to safely extract tenant_id from request state.
    Returns None if not set.
    """
    return getattr(request.state, "tenant_id", None)


def require_tenant_context(request: Request) -> UUID:
    """Extract tenant_id, raising error if not set.

    Utility for endpoints that require tenant context.
    Raises HTTPException with 401 if tenant_id is missing.
    """
    from fastapi import HTTPException, status

    tenant_id = get_tenant_id_from_request(request)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )
    return tenant_id
