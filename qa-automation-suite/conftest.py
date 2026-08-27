import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# The app creates its default engine and runs Base.metadata.create_all() at
# import time. Point it at a throwaway file before import so tests never
# touch a real noc.db or require Postgres to be reachable.
_BOOTSTRAP_DB = Path(tempfile.gettempdir()) / "qa_automation_bootstrap.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_BOOTSTRAP_DB}")
os.environ.setdefault("SIMULATED_LATENCY_MS", "0")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def db_session(tmp_path):
    """A fresh, isolated SQLite-backed session per test."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """A TestClient wired to the isolated db_session instead of the app's real DB."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def report_payload():
    """Factory for a valid /reports payload, overridable per test."""

    def _make(**overrides):
        payload = {
            "station_id": "STATION-001",
            "timestamp": "2024-06-01T10:00:00Z",
            "connectivity_status": "online",
            "latency_ms": 50,
            "error_count": 0,
            "firmware_version": "v1.0.0",
        }
        payload.update(overrides)
        return payload

    return _make
