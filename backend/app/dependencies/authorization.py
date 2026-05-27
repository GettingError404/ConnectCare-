"""Reusable authorization dependencies for FastAPI routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import get_current_user
from app.db.session import get_db
from app.middleware.tenant_context import require_tenant_context
from app.models.user import User
from app.services.rbac import AuthorizationService


def _get_scope_ids(request: Request) -> tuple[UUID | None, UUID | None]:
    organization_id_value = request.path_params.get("org_id") or request.path_params.get("organization_id")
    organization_unit_id_value = (
        request.path_params.get("unit_id") or request.path_params.get("organization_unit_id")
    )

    organization_id = UUID(str(organization_id_value)) if organization_id_value else None
    organization_unit_id = UUID(str(organization_unit_id_value)) if organization_unit_id_value else None
    return organization_id, organization_unit_id


def require_permission(permission: str):
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        tenant_id = require_tenant_context(request)
        organization_id, organization_unit_id = _get_scope_ids(request)

        service = AuthorizationService(db)
        logger = get_logger(__name__)
        try:
            service.require_permission(
                current_user,
                permission,
                tenant_id,
                organization_id=organization_id,
                organization_unit_id=organization_unit_id,
            )
        except Exception as e:
            logger.warning(
                "authorization_failure",
                extra={
                    "permission": permission,
                    "tenant_id": str(tenant_id),
                    "user_id": getattr(current_user, "id", None),
                    "user_role": getattr(getattr(current_user, "user_roles", None), "role", None),
                    "error": str(e),
                },
            )
            raise

        return current_user

    return dependency


def require_any_permission(permissions: list[str]):
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        tenant_id = require_tenant_context(request)
        organization_id, organization_unit_id = _get_scope_ids(request)

        service = AuthorizationService(db)
        logger = get_logger(__name__)
        try:
            service.require_any_permission(
                current_user,
                permissions,
                tenant_id,
                organization_id=organization_id,
                organization_unit_id=organization_unit_id,
            )
        except Exception as e:
            logger.warning(
                "authorization_failure",
                extra={
                    "permissions": permissions,
                    "tenant_id": str(tenant_id),
                    "user_id": getattr(current_user, "id", None),
                    "error": str(e),
                },
            )
            raise

        return current_user

    return dependency


def require_role(role_slug: str):
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        tenant_id = require_tenant_context(request)
        service = AuthorizationService(db)
        logger = get_logger(__name__)
        try:
            service.require_role(
                current_user,
                role_slug,
                tenant_id,
            )
        except Exception as e:
            logger.warning(
                "authorization_failure",
                extra={
                    "role": role_slug,
                    "tenant_id": str(tenant_id),
                    "user_id": getattr(current_user, "id", None),
                    "error": str(e),
                },
            )
            raise

        return current_user

    return dependency

