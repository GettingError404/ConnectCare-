"""Optional hook functions for auth flows.

Kept separate to avoid circular imports if needed.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.services.rbac_seeding import assign_default_role_to_user


def assign_default_role_after_register(db: Session, user_id: UUID, tenant_id: UUID) -> None:
    assign_default_role_to_user(db=db, user_id=user_id, tenant_id=tenant_id)

