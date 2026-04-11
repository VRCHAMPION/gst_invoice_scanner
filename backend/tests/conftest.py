"""
conftest.py — Shared fixtures for all integration tests.

Uses an in-memory SQLite database so no external services are needed.
The get_db dependency is overridden to use the test DB session.
"""
import os
import sys

# Ensure backend/ is on the path regardless of where pytest is invoked from
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set env vars BEFORE importing any app modules (they read env at import time)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_ci.db")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-ci-only")
os.environ.setdefault("GEMINI_API_KEY", "fake-key-for-tests")
os.environ.setdefault("IS_PRODUCTION", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

# ── In-memory SQLite engine ───────────────────────────────────────────
TEST_DATABASE_URL = "sqlite://"  # pure in-memory

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once for the test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    """TestClient with DB dependency overridden to use in-memory SQLite."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client):
    """Register a unique user per test and return their credentials + response data."""
    import uuid
    unique_email = f"owner_{uuid.uuid4().hex[:8]}@test.com"
    payload = {"name": "Test Owner", "email": unique_email, "password": "securepass123"}
    resp = client.post("/api/register", json=payload)
    assert resp.status_code == 200, resp.text
    return {"credentials": payload, "data": resp.json()}


@pytest.fixture()
def auth_client(client, registered_user):
    """TestClient that is already logged in as the registered user."""
    creds = registered_user["credentials"]
    resp = client.post("/api/login", json={"email": creds["email"], "password": creds["password"]})
    assert resp.status_code == 200, resp.text
    return client
