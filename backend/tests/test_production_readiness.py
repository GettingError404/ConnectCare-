from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app


def test_production_secret_key_validation_rejects_default_secret():
    with pytest.raises(ValueError):
        Settings(ENV="production", SECRET_KEY="changeme-in-production")


def test_security_headers_are_applied_to_api_responses():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "strict-transport-security" in response.headers