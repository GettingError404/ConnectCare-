from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt

from app.api.v1 import auth as auth_module
from app.core import security as security_module
from app.core.login_protection import login_protection
from app.core.security import create_access_token, create_refresh_token, get_current_user
from app.main import app
from app.models.auth import UserSession
from app.models.user import User
from app.services import auth_service
from app.services.rbac import AuthorizationService


class FakeDB:
    def __init__(self, user=None, session=None):
        self.user = user
        self.session = session

    def get(self, model, primary_key):
        if model is User and self.user and str(self.user.id) == str(primary_key):
            return self.user
        if model is UserSession and self.session and str(self.session.id) == str(primary_key):
            return self.session
        return None


class FakeRepo:
    def __init__(self, stored_token=None, session=None):
        self.stored_token = stored_token
        self.session = session
        self.revoked_families: list[str] = []
        self.revoked_jtis: list[str] = []
        self.created_records: list[dict] = []

    def get_by_jti(self, jti: str):
        if self.stored_token and self.stored_token.jti == jti:
            return self.stored_token
        return None

    def revoke_family(self, family_id: str):
        self.revoked_families.append(family_id)
        if self.stored_token and self.stored_token.family_id == family_id:
            self.stored_token.revoked = True

    def revoke(self, jti: str, replaced_by: str | None = None):
        self.revoked_jtis.append(jti)
        if self.stored_token and self.stored_token.jti == jti:
            self.stored_token.revoked = True
            self.stored_token.replaced_by = replaced_by

    def create(self, **kwargs):
        self.created_records.append(kwargs)
        return SimpleNamespace(**kwargs)


@pytest.fixture()
def client():
    return TestClient(app)


def test_openapi_auth_schema_and_protected_security():
    spec = app.openapi()

    login_post = spec["paths"]["/api/v1/auth/login"]["post"]
    login_request = login_post["requestBody"]["content"]["application/x-www-form-urlencoded"]["schema"]
    login_schema = spec["components"]["schemas"][login_request["$ref"].split("/")[-1]]

    assert {"username", "password"}.issubset(login_schema["properties"].keys())
    assert spec["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"] == "/api/v1/auth/login"
    assert spec["paths"]["/api/v1/auth/logout_all"]["post"]["security"]
    assert spec["paths"]["/api/v1/rbac/permissions"]["get"]["security"]


def test_swagger_login_form_flow_and_validation(client, monkeypatch):
    login_protection._memory.clear()

    def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(auth_module, "authenticate_user", lambda db, payload: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(auth_module, "create_token_pair", lambda db, user: {"access_token": "access", "refresh_token": "refresh", "token_type": "bearer"})
    app.dependency_overrides[auth_module.get_db] = fake_get_db

    try:
        response = client.post("/api/v1/auth/login", data={"username": "swagger-success@example.com", "password": "secret"})
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"

        missing_password = client.post("/api/v1/auth/login", data={"username": "swagger-success@example.com"})
        assert missing_password.status_code == 422
    finally:
        app.dependency_overrides.clear()
        login_protection._memory.clear()


def test_get_current_user_rejects_invalid_signature_missing_session_tenant_mismatch_and_revoked_session():
    tenant_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()
    user = SimpleNamespace(id=user_id, tenant_id=tenant_id)
    session = SimpleNamespace(id=session_id, user_id=user_id, revoked=False)
    db = FakeDB(user=user, session=session)

    valid_token = create_access_token({"sub": str(user_id), "user_id": str(user_id), "session_id": str(session_id), "tenant_id": str(tenant_id)})
    assert get_current_user(token=valid_token, db=db) == user

    invalid_signature = jwt.encode(
        {"sub": str(user_id), "user_id": str(user_id), "session_id": str(session_id), "tenant_id": str(tenant_id)},
        "wrong-secret",
        algorithm=security_module.ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=invalid_signature, db=db)
    assert exc_info.value.status_code == 401

    missing_session_token = create_access_token({"sub": str(user_id), "user_id": str(user_id), "tenant_id": str(tenant_id)})
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=missing_session_token, db=db)
    assert exc_info.value.status_code == 401

    tenant_mismatch_token = create_access_token({"sub": str(user_id), "user_id": str(user_id), "session_id": str(session_id), "tenant_id": str(uuid4())})
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=tenant_mismatch_token, db=db)
    assert exc_info.value.status_code == 401

    revoked_db = FakeDB(user=user, session=SimpleNamespace(id=session_id, user_id=user_id, revoked=True))
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=valid_token, db=revoked_db)
    assert exc_info.value.status_code == 401


def test_refresh_rotation_rejects_revoked_session_and_prevents_replay(monkeypatch):
    tenant_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()
    family_id = "family-1"
    jti = "jti-1"
    user = SimpleNamespace(id=user_id, tenant_id=tenant_id, user_roles=[])
    session = SimpleNamespace(id=session_id, revoked=True)
    stored = SimpleNamespace(jti=jti, family_id=family_id, user_id=user_id, session_id=session_id, revoked=False, replaced_by=None)
    db = FakeDB(user=user, session=session)
    refresh_repo = FakeRepo(stored_token=stored, session=session)
    session_repo = SimpleNamespace(get_session=lambda session_key: session)

    monkeypatch.setattr(auth_service, "RefreshTokenRepository", lambda db_obj: refresh_repo)
    monkeypatch.setattr(auth_service, "SessionRepository", lambda db_obj: session_repo)

    refresh_token = create_refresh_token({"sub": str(user_id), "user_id": str(user_id), "session_id": str(session_id), "family_id": family_id, "jti": jti})

    with pytest.raises(HTTPException) as exc_info:
        auth_service.rotate_refresh_token(db, refresh_token)
    assert exc_info.value.status_code == 401
    assert refresh_repo.revoked_families == [family_id]

    session.revoked = False
    refresh_repo.stored_token.revoked = False
    refresh_repo.revoked_families.clear()
    rotated = auth_service.rotate_refresh_token(db, refresh_token)
    assert rotated["token_type"] == "bearer"
    assert refresh_repo.stored_token.revoked is True

    with pytest.raises(HTTPException) as exc_info:
        auth_service.rotate_refresh_token(db, refresh_token)
    assert exc_info.value.status_code == 401


def test_rbac_route_blocks_normal_user_and_allows_admin(client, monkeypatch):
    tenant_id = uuid4()
    normal_user = SimpleNamespace(id=uuid4(), tenant_id=tenant_id, role_slug="user")
    admin_user = SimpleNamespace(id=uuid4(), tenant_id=tenant_id, role_slug="admin")
    token = create_access_token({"sub": str(normal_user.id), "user_id": str(normal_user.id), "session_id": str(uuid4()), "tenant_id": str(tenant_id)})

    def fake_get_db():
        yield SimpleNamespace()

    def fake_require_permission(self, current_user, permission, tenant_id, organization_id=None, organization_unit_id=None):
        if getattr(current_user, "role_slug", None) != "admin":
            raise HTTPException(status_code=403, detail="Permission denied")

    monkeypatch.setattr(AuthorizationService, "require_permission", fake_require_permission)
    monkeypatch.setattr(
        "app.api.v1.rbac.PermissionService.list_permissions",
        lambda self, skip=0, limit=100: [
            SimpleNamespace(
                id=uuid4(),
                resource="rbac",
                action="view",
                description="view",
                created_at=datetime(2026, 5, 22, tzinfo=timezone.utc),
            )
        ],
    )

    app.dependency_overrides.clear()
    app.dependency_overrides[auth_module.get_db] = fake_get_db
    app.dependency_overrides[auth_module.get_current_user] = lambda: normal_user

    try:
        forbidden = client.get("/api/v1/rbac/permissions", headers={"Authorization": f"Bearer {token}"})
        assert forbidden.status_code == 403

        app.dependency_overrides[auth_module.get_current_user] = lambda: admin_user
        allowed = client.get("/api/v1/rbac/permissions", headers={"Authorization": f"Bearer {token}"})
        assert allowed.status_code == 200
    finally:
        app.dependency_overrides.clear()