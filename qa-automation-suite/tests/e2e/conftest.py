import os
import uuid

import httpx
import pytest

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session", autouse=True)
def _require_live_service():
    """Skip the whole e2e tier if nothing is actually running at BASE_URL.

    Unlike tests/unit and tests/integration, these tests never start the app
    themselves - they assume a real, already-running instance (local uvicorn
    or `docker compose up`), so they can observe genuine network/DB behavior.
    """
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=2)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        pytest.skip(
            f"No live service reachable at {BASE_URL} ({exc}). Start it with "
            "`uvicorn app.main:app` or `docker compose up` before running tests/e2e."
        )


@pytest.fixture()
def api_client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        yield client


@pytest.fixture()
def unique_station_id():
    # The e2e tier shares a real, persistent database with whatever else has
    # talked to the live service, so every test needs its own station_id to
    # avoid colliding with leftover or concurrently-created data.
    return f"E2E-STATION-{uuid.uuid4().hex[:12]}"


@pytest.fixture()
def report_payload(unique_station_id):
    def _make(**overrides):
        payload = {
            "station_id": unique_station_id,
            "timestamp": "2024-06-01T10:00:00Z",
            "connectivity_status": "online",
            "latency_ms": 50,
            "error_count": 0,
            "firmware_version": "v1.0.0",
        }
        payload.update(overrides)
        return payload

    return _make
