from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1 import auth as auth_module
from app.core.config import Settings
from app.core.login_protection import login_protection
from app.main import app
from app.db.session import engine


def test_settings_validate_trusted_hosts_in_production():
    settings = Settings(
        ENV="production",
        SECRET_KEY="x" * 32,
        TRUSTED_HOSTS="api.example.com",
    )
    assert settings.TRUSTED_HOSTS == "api.example.com"


def test_engine_has_pool_tuning():
    pool = engine.pool
    assert getattr(pool, "_recycle", None) is not None
    assert getattr(pool, "_timeout", None) is not None


def test_trusted_host_middleware_blocks_untrusted_host():
    client = TestClient(app)
    response = client.get("/health", headers={"host": "evil.example.com"})
    assert response.status_code == 400


def test_login_rate_limit_blocks_bruteforce(monkeypatch):
    client = TestClient(app)
    login_protection._memory.clear()

    def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(login_protection, "redis", None)
    monkeypatch.setattr(login_protection, "attempt_limit", 2)
    monkeypatch.setattr(login_protection, "attempt_window_seconds", 60)
    monkeypatch.setattr(login_protection, "lockout_seconds", 300)
    monkeypatch.setattr(auth_module, "authenticate_user", lambda db, payload: (_ for _ in ()).throw(HTTPException(status_code=401, detail="Invalid credentials")))
    app.dependency_overrides[auth_module.get_db] = fake_get_db

    try:
        first = client.post("/api/v1/auth/login", data={"username": "user@example.com", "password": "bad"})
        second = client.post("/api/v1/auth/login", data={"username": "user@example.com", "password": "bad"})
        third = client.post("/api/v1/auth/login", data={"username": "user@example.com", "password": "bad"})

        assert first.status_code == 401
        assert second.status_code == 429
        assert third.status_code == 429
    finally:
        app.dependency_overrides.clear()
        login_protection._memory.clear()


def test_trace_header_is_propagated():
    client = TestClient(app)
    response = client.get("/health", headers={"X-Trace-ID": "trace-123"})
    assert response.status_code == 200
    assert response.headers["x-trace-id"] == "trace-123"


def test_request_body_limit_rejects_oversized_payload(monkeypatch):
    client = TestClient(app)
    login_protection._memory.clear()

    def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(auth_module, "authenticate_user", lambda db, payload: SimpleNamespace(id="user-1"))
    monkeypatch.setattr(auth_module, "create_token_pair", lambda db, user: {"access_token": "access", "refresh_token": "refresh", "token_type": "bearer"})
    app.dependency_overrides[auth_module.get_db] = fake_get_db

    try:
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "size-test@example.com", "password": "x" * 2_000_000},
        )
        assert response.status_code == 413
    finally:
        app.dependency_overrides.clear()
        login_protection._memory.clear()