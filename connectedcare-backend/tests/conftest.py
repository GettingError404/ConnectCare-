import os
import pytest

from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.db.session import engine, SessionLocal


@pytest.fixture(scope="session")
def app():
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    return TestClient(app)


@pytest.fixture()
def db_session():
    """Provide a DB session for tests. Skip if DB is not reachable."""
    try:
        conn = engine.connect()
        conn.close()
    except Exception:
        pytest.skip("Database not available; set DATABASE_URL to run DB tests")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
