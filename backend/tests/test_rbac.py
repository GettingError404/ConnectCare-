import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.db.session import SessionLocal
from app.models.rbac import Permission
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.rbac import AssignRoleRequest, RoleCreate
from app.services.rbac import AuthorizationService, RoleService


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


def random_email() -> str:
    return f"rbac+{uuid.uuid4().hex[:8]}@example.com"


def create_test_user(db_session, tenant_id=None) -> User:
    user = User(
        email=random_email(),
        full_name="RBAC Test User",
        password_hash="hash",
        tenant_id=tenant_id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_test_tenant(db_session, slug: str) -> Tenant:
    tenant = Tenant(name=f"Tenant {slug}", slug=slug)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.mark.timeout(30)
def test_role_assignment_and_permission_aggregation(db_session):
    tenant = create_test_tenant(db_session, f"tenant-{uuid.uuid4().hex[:8]}")
    tenant_id = tenant.id
    role_service = RoleService(db_session, tenant_id)

    base_role = role_service.create_role(
        RoleCreate(name="Base Clinical", slug=f"base-clinical-{uuid.uuid4().hex[:8]}")
    )
    child_role = role_service.create_role(
        RoleCreate(
            name="Child Clinical",
            slug=f"child-clinical-{uuid.uuid4().hex[:8]}",
            parent_role_id=base_role.id,
        )
    )

    permission_resource = f"rbac-test-{uuid.uuid4().hex[:8]}"
    permission = Permission(resource=permission_resource, action="read", description="Read vitals")
    db_session.add(permission)
    db_session.commit()
    base_role.permissions.append(permission)
    db_session.commit()

    permission_service = AuthorizationService(db_session)
    user = create_test_user(db_session, tenant_id=tenant_id)

    assignment = permission_service.assign_role(
        AssignRoleRequest(user_id=user.id, role_id=child_role.id),
        assigned_by=None,
        tenant_id=tenant_id,
    )
    assert assignment.is_active is True

    permissions = permission_service.get_user_permissions(user.id, tenant_id)
    assert isinstance(permissions, list)
    assert f"{permission_resource}:read" in permissions


@pytest.mark.timeout(30)
def test_tenant_isolation_blocks_cross_tenant_access(db_session):
    tenant_a = create_test_tenant(db_session, f"tenant-a-{uuid.uuid4().hex[:8]}")
    tenant_b = create_test_tenant(db_session, f"tenant-b-{uuid.uuid4().hex[:8]}")
    role_a_service = RoleService(db_session, tenant_a.id)
    role_b_service = RoleService(db_session, tenant_b.id)

    role_a = role_a_service.create_role(RoleCreate(name="Tenant A Role", slug=f"tenant-a-{uuid.uuid4().hex[:8]}"))
    role_b_service.create_role(RoleCreate(name="Tenant B Role", slug=f"tenant-b-{uuid.uuid4().hex[:8]}"))

    user = create_test_user(db_session, tenant_id=tenant_a.id)
    authz = AuthorizationService(db_session)

    with pytest.raises(HTTPException):
        authz.assign_role(AssignRoleRequest(user_id=user.id, role_id=role_a.id), assigned_by=None, tenant_id=tenant_b.id)


@pytest.mark.timeout(30)
def test_expired_roles_are_ignored(db_session):
    tenant = create_test_tenant(db_session, f"tenant-expired-{uuid.uuid4().hex[:8]}")
    tenant_id = tenant.id
    role_service = RoleService(db_session, tenant_id)
    role = role_service.create_role(RoleCreate(name="Expiring Role", slug=f"expiring-{uuid.uuid4().hex[:8]}"))
    user = create_test_user(db_session, tenant_id=tenant_id)
    authz = AuthorizationService(db_session)

    authz.assign_role(
        AssignRoleRequest(user_id=user.id, role_id=role.id, expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)),
        assigned_by=None,
        tenant_id=tenant_id,
    )

    permissions = authz.get_user_permissions(user.id, tenant_id)
    assert permissions == []
