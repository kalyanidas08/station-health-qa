import time


def test_simulated_latency_middleware_delays_responses(client, monkeypatch):
    """SIMULATED_LATENCY_MS is what makes local (0ms) and Docker (40ms)
    behave differently under timing - see service/README.md. main.py reads
    the env var into a module-level constant once at import time, so setting
    the env var here would have no effect (the app was already imported by
    conftest.py). The middleware body re-reads that module-level name on
    every request, so patching it directly exercises the real delay path
    without needing to reimport the app.

    Asserts only a floor, never a ceiling: asyncio.sleep() guarantees *at
    least* the requested duration but can run longer under scheduler load,
    so a floor is the non-flaky way to prove the delay actually happened.
    """
    monkeypatch.setattr("app.main._LATENCY_MS", 100)

    start = time.perf_counter()
    response = client.get("/health")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms >= 100


def test_no_latency_by_default(client):
    # Contrast case: with no simulated latency configured (the default our
    # fixtures use), a request should return quickly - well under the 100ms
    # floor asserted above.
    start = time.perf_counter()
    response = client.get("/health")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 100
