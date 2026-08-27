import pytest


def test_get_station_status_returns_404_for_unknown_station(client):
    response = client.get("/stations/UNKNOWN-STATION/status")

    assert response.status_code == 404


def test_get_station_status_returns_latest_by_timestamp_not_insertion_order(client, report_payload):
    station_id = "STATION-ORDER"
    newer = report_payload(station_id=station_id, timestamp="2024-06-01T12:00:00Z", firmware_version="v2.0.0")
    older = report_payload(station_id=station_id, timestamp="2024-06-01T09:00:00Z", firmware_version="v1.0.0")

    # Insert the newer report first, older second - deliberately out of order.
    client.post("/reports", json=newer)
    client.post("/reports", json=older)

    response = client.get(f"/stations/{station_id}/status")

    assert response.status_code == 200
    assert response.json()["firmware_version"] == "v2.0.0"


def test_list_stations_returns_one_entry_per_station(client, report_payload):
    client.post("/reports", json=report_payload(station_id="STATION-A"))
    client.post("/reports", json=report_payload(station_id="STATION-B"))
    client.post("/reports", json=report_payload(station_id="STATION-A", timestamp="2024-06-01T11:00:00Z"))

    response = client.get("/stations")

    assert response.status_code == 200
    station_ids = [s["station_id"] for s in response.json()]
    assert sorted(station_ids) == ["STATION-A", "STATION-B"]


def test_poor_hygiene_lists_only_flagged_stations(client, report_payload):
    healthy = report_payload(
        station_id="STATION-HEALTHY", connectivity_status="online", error_count=0, latency_ms=0
    )
    unhealthy = report_payload(
        station_id="STATION-UNHEALTHY", connectivity_status="offline", error_count=10, latency_ms=500
    )

    client.post("/reports", json=healthy)
    client.post("/reports", json=unhealthy)

    response = client.get("/stations/poor-hygiene")

    assert response.status_code == 200
    flagged_ids = [s["station_id"] for s in response.json()]
    assert flagged_ids == ["STATION-UNHEALTHY"]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: list_stations() finds the latest report per station via "
        "MAX(timestamp), then joins back on (station_id, timestamp). Two "
        "reports for the same station with an identical timestamp both match "
        "that join, so the station appears twice in /stations instead of once."
    ),
)
def test_list_stations_does_not_duplicate_station_on_identical_timestamps(client, report_payload):
    duplicate_payload = report_payload(station_id="STATION-DUP", timestamp="2024-06-01T10:00:00Z")

    client.post("/reports", json=duplicate_payload)
    client.post("/reports", json={**duplicate_payload, "error_count": 5})

    response = client.get("/stations")

    matches = [s for s in response.json() if s["station_id"] == "STATION-DUP"]
    assert len(matches) == 1


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: get_poor_hygiene_stations() uses the same MAX(timestamp) + "
        "join-back pattern as list_stations(). Two reports for the same "
        "flagged station with an identical timestamp both match the join, so "
        "the station appears twice in /stations/poor-hygiene - the NOC's "
        "action list would show one broken station as two."
    ),
)
def test_poor_hygiene_does_not_duplicate_station_on_identical_timestamps(client, report_payload):
    duplicate_payload = report_payload(
        station_id="STATION-DUP-FLAGGED",
        timestamp="2024-06-01T10:00:00Z",
        connectivity_status="offline",
        error_count=10,
        latency_ms=500,
    )

    client.post("/reports", json=duplicate_payload)
    client.post("/reports", json={**duplicate_payload, "error_count": 8})

    response = client.get("/stations/poor-hygiene")

    matches = [s for s in response.json() if s["station_id"] == "STATION-DUP-FLAGGED"]
    assert len(matches) == 1


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: station_id has no character restrictions in the schema (only "
        "min_length=1), but it's later embedded as a raw path segment in "
        "GET /stations/{station_id}/status. A station_id containing '/' - "
        "plausible for a hierarchical asset code like 'SITE-A/CHARGER-01' - "
        "ingests successfully via POST /reports, but the router then sees an "
        "extra path segment and returns 404 instead of matching the station: "
        "data that was written can never be read back through this endpoint."
    ),
)
def test_station_id_with_slash_is_retrievable_via_status(client, report_payload):
    station_id = "SITE-A/CHARGER-01"
    payload = report_payload(station_id=station_id)

    post_response = client.post("/reports", json=payload)
    assert post_response.status_code == 201

    status_response = client.get(f"/stations/{station_id}/status")
    assert status_response.status_code == 200
