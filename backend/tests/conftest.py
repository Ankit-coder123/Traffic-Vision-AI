"""
Shared fixtures for the TrafficVision AI backend test suite.

Design notes
------------
- Tests never touch the real Postgres database. `app.database.engine` and
  `app.database.SessionLocal` are monkey-patched to point at an in-memory
  SQLite database *before* `app.main` is imported -- `app.main` runs
  `Base.metadata.create_all(bind=engine)` at import time, so the patch has
  to happen first or it would try (and fail) to connect to a real Postgres
  server.
- `app.database.get_db()` looks up `SessionLocal` as a module-level global
  at call time, so patching `app.database.SessionLocal` is enough to
  redirect every request's DB session -- no need to override the
  `get_db` FastAPI dependency separately.
- Each test function gets a freshly wiped schema (autouse `_reset_db`
  fixture) so tests never leak state into one another, and can freely
  assume "first user signed up = becomes admin" without interference from
  other tests.
- `StaticPool` is required for SQLite `:memory:` under FastAPI's TestClient
  -- without it, each new connection would see an empty, unrelated
  in-memory database (SQLite's default is one throwaway DB per connection).
"""
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-use")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

import app.database as database  # noqa: E402

database.engine = test_engine
database.SessionLocal = TestSessionLocal

from app.main import app  # noqa: E402  (import AFTER the engine patch above)
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    """Wipe and recreate every table before each test function."""
    database.Base.metadata.drop_all(bind=test_engine)
    database.Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def _signup_and_login(client, *, email, password, name, role):
    signup_resp = client.post(
        "/auth/signup",
        json={"name": name, "email": email, "password": password, "role": role},
    )
    assert signup_resp.status_code == 201, signup_resp.text
    user = signup_resp.json()

    login_resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    return {
        "token": token,
        "user": user,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture()
def admin_auth(client):
    """The FIRST user ever created in a test's fresh DB -- this is what
    triggers the bootstrap-admin path in POST /auth/signup. Every other
    role fixture depends on this one (directly or via fixture ordering)
    so it always runs first and 'admin' is granted for real, not silently
    downgraded to 'user'."""
    return _signup_and_login(
        client, email="admin@test.com", password="AdminPass123!", name="Admin User", role="admin"
    )


@pytest.fixture()
def operator_auth(client, admin_auth):
    return _signup_and_login(
        client, email="operator@test.com", password="OperatorPass123!", name="Operator User", role="operator"
    )


@pytest.fixture()
def user_auth(client, admin_auth):
    return _signup_and_login(
        client, email="user@test.com", password="UserPass123!", name="Regular User", role="user"
    )


@pytest.fixture()
def zone(client, admin_auth):
    """A single traffic zone, created by the admin -- most other
    endpoints (traffic data, predictions, incidents, analytics) need at
    least one zone to operate on."""
    resp = client.post(
        "/traffic/zones",
        json={"name": "MG Road Junction", "latitude": 12.9716, "longitude": 77.5946, "road_type": "arterial"},
        headers=admin_auth["headers"],
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# NOTE: no other test-support functions belong in this file. conftest.py
# is auto-loaded by pytest as its own module; if a test file also did
# `from tests.conftest import <name>`, Python would import this file a
# SECOND time under a different module identity and re-run the engine
# patching below against a throwaway, table-less database (see
# tests/helpers.py's docstring for the full failure mode). Shared,
# side-effect-free test utilities go in tests/helpers.py instead.
