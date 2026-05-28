from __future__ import annotations

import logging
from typing import Optional, Tuple
from uuid import UUID

from fastapi import WebSocket
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.auth import UserSession
from app.models.user import User

logger = logging.getLogger(__name__)


async def authenticate_websocket(
    *,
    websocket: WebSocket,
    token: str,
    tenant_id: Optional[str] = None,
) -> Tuple[User, UUID, UUID]:
    """Validate JWT during WS connect.

    Returns: (user, tenant_id, session_id)
    """
    # Token validation
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        await websocket.close(code=4003)
        raise

    user_id = payload.get("sub") or payload.get("user_id")
    session_id_raw = payload.get("session_id")
    token_tenant_raw = payload.get("tenant_id")

    if not user_id or not session_id_raw:
        await websocket.close(code=4003)
        raise JWTError("missing claims")

    try:
        user_uuid = UUID(str(user_id))
        session_uuid = UUID(str(session_id_raw))
    except ValueError:
        await websocket.close(code=4003)
        raise

    effective_tenant: Optional[UUID] = None
    if token_tenant_raw:
        try:
            effective_tenant = UUID(str(token_tenant_raw))
        except ValueError:
            effective_tenant = None

    if tenant_id:
        try:
            tenant_uuid = UUID(str(tenant_id))
        except ValueError:
            await websocket.close(code=4003)
            raise
        if effective_tenant and tenant_uuid != effective_tenant:
            await websocket.close(code=4003)
            raise JWTError("tenant mismatch")
        effective_tenant = tenant_uuid

    if not effective_tenant:
        await websocket.close(code=4003)
        raise JWTError("missing tenant_id")

    # Validate server-side session state (revoked, user match)
    # get_db is sync; run in thread is overkill here; reuse current pattern (db is sync).
    db: Session = next(get_db()) if callable(get_db) else None  # fallback safety
    # But get_db returns a generator dependency; call properly
    # We'll import directly to avoid dependency container complexity.
    from app.db.session import get_db as _get_db

    db = next(_get_db())
    try:
        user = db.get(User, user_uuid)
        session = db.get(UserSession, session_uuid)
        if not user or not session or session.revoked or str(session.user_id) != str(user.id):
            await websocket.close(code=4003)
            raise JWTError("invalid or revoked session")
    finally:
        db.close()

    return user, effective_tenant, session_uuid

