import pytest


def test_metrics_summary_on_empty_database(client):
    response = client.get("/metrics/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_stations": 0,
        "online_count": 0,
        "offline_count": 0,
        "flagged_count": 0,
        "average_latency_ms": None,
        "total_error_count": 0,
    }


def test_metrics_summary_aggregates_latest_reports(client, report_payload):
    client.post(
        "/reports",
        json=report_payload(station_id="STATION-A", connectivity_status="online", latency_ms=100, error_count=1),
    )
    client.post(
        "/reports",
        json=report_payload(station_id="STATION-B", connectivity_status="offline", latency_ms=300, error_count=10),
    )

    response = client.get("/metrics/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_stations"] == 2
    assert body["online_count"] == 1
    assert body["offline_count"] == 1
    assert body["total_error_count"] == 11
    assert body["average_latency_ms"] == pytest.approx((100 + 300) / 2)


def test_metrics_summary_only_counts_latest_report_per_station(client, report_payload):
    station_id = "STATION-A"
    client.post(
        "/reports",
        json=report_payload(station_id=station_id, timestamp="2024-06-01T09:00:00Z", latency_ms=500, error_count=10),
    )
    client.post(
        "/reports",
        json=report_payload(station_id=station_id, timestamp="2024-06-01T10:00:00Z", latency_ms=50, error_count=0),
    )

    response = client.get("/metrics/summary")

    body = response.json()
    assert body["total_stations"] == 1
    assert body["average_latency_ms"] == pytest.approx(50)
    assert body["total_error_count"] == 0


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: get_metrics_summary() uses the same MAX(timestamp) + join-back "
        "pattern as list_stations(). Two reports for the same station with an "
        "identical timestamp both match the join, so that station is counted "
        "twice - inflating total_stations, flagged_count, total_error_count, "
        "and skewing average_latency_ms network-wide."
    ),
)
def test_metrics_summary_does_not_double_count_identical_timestamps(client, report_payload):
    duplicate_payload = report_payload(
        station_id="STATION-DUP", timestamp="2024-06-01T10:00:00Z", latency_ms=100, error_count=1
    )

    client.post("/reports", json=duplicate_payload)
    client.post("/reports", json={**duplicate_payload, "error_count": 3})

    response = client.get("/metrics/summary")

    body = response.json()
    assert body["total_stations"] == 1
    assert body["total_error_count"] == 3


def test_metrics_summary_counts_flagged_stations_correctly(client, report_payload):
    # flagged_count is never asserted by the other tests above. Including a
    # station that is offline but otherwise perfect - landing exactly on the
    # flagging threshold (score 60.0) - checks the aggregate respects the
    # same exclusive boundary as is_flagged(), not just "offline == flagged".
    client.post(
        "/reports",
        json=report_payload(
            station_id="STATION-BORDERLINE", connectivity_status="offline", error_count=0, latency_ms=0
        ),
    )
    client.post(
        "/reports",
        json=report_payload(
            station_id="STATION-FLAGGED", connectivity_status="offline", error_count=10, latency_ms=500
        ),
    )
    client.post(
        "/reports",
        json=report_payload(station_id="STATION-HEALTHY", connectivity_status="online", error_count=0, latency_ms=0),
    )

    response = client.get("/metrics/summary")

    body = response.json()
    assert body["total_stations"] == 3
    assert body["flagged_count"] == 1
    assert body["offline_count"] == 2
    assert body["online_count"] == 1


def test_metrics_summary_rounds_average_latency_to_two_decimals(client, report_payload):
    # 10 + 10 + 11 = 31 / 3 = 10.333... - a genuinely repeating decimal,
    # unlike the round-number latencies used in the other aggregate tests.
    for i, latency in enumerate([10, 10, 11]):
        client.post("/reports", json=report_payload(station_id=f"STATION-{i}", latency_ms=latency))

    response = client.get("/metrics/summary")

    assert response.json()["average_latency_ms"] == pytest.approx(10.33)


@pytest.mark.parametrize("method", ["post", "put", "delete", "patch"])
def test_metrics_summary_rejects_disallowed_http_methods(client, method):
    response = getattr(client, method)("/metrics/summary")

    assert response.status_code == 405
