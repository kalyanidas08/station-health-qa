import pytest


def test_ingest_report_returns_computed_score_and_flag(client, report_payload):
    # penalty: latency 100/20=5, errors 2*5=10 -> 100 - 15 = 85
    payload = report_payload(latency_ms=100, error_count=2)

    response = client.post("/reports", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["station_id"] == payload["station_id"]
    assert body["hygiene_score"] == pytest.approx(85.0)
    assert body["flagged"] is False


def test_ingest_report_persists_and_is_queryable_via_status(client, report_payload):
    payload = report_payload(station_id="STATION-XYZ")

    client.post("/reports", json=payload)
    response = client.get(f"/stations/{payload['station_id']}/status")

    assert response.status_code == 200
    body = response.json()
    assert body["station_id"] == "STATION-XYZ"
    assert body["connectivity_status"] == payload["connectivity_status"]
    assert body["firmware_version"] == payload["firmware_version"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"connectivity_status": "flaky"},
        {"latency_ms": -1},
        {"error_count": -1},
        {"station_id": ""},
        {"firmware_version": ""},
    ],
)
def test_ingest_rejects_invalid_payloads(client, report_payload, overrides):
    payload = report_payload(**overrides)

    response = client.post("/reports", json=payload)

    assert response.status_code == 422


def test_ingest_rejects_missing_required_field(client, report_payload):
    payload = report_payload()
    del payload["station_id"]

    response = client.post("/reports", json=payload)

    assert response.status_code == 422


def test_ingest_does_not_reject_or_dedupe_repeated_station_and_timestamp(client, report_payload):
    # Documents current behavior, not a defect in itself: there's no uniqueness
    # constraint on (station_id, timestamp), so a repeated pair is silently
    # accepted rather than rejected (409) or upserted. Whether that's correct
    # depends on intent (immutable event log vs. latest-state table) - the
    # assignment doesn't specify. What IS a proven defect is that the
    # "latest per station" read queries assume this pair is unique and break
    # that assumption without noticing - see the xfail tests in
    # test_stations.py and test_metrics.py for the concrete consequences.
    payload = report_payload()

    first = client.post("/reports", json=payload)
    second = client.post("/reports", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201


def test_ingest_ignores_unexpected_extra_fields(client, report_payload):
    # Pydantic v2 defaults to ignoring unrecognized fields rather than
    # rejecting the request (no `model_config = {"extra": "forbid"}` is set
    # on ReportIn), so a client sending an unexpected field is silently
    # accepted rather than getting a 422.
    payload = report_payload()
    payload["unexpected_field"] = "should be ignored, not rejected"

    response = client.post("/reports", json=payload)

    assert response.status_code == 201


@pytest.mark.parametrize("connectivity_status", ["Online", "OFFLINE", "Offline", "ONLINE"])
def test_ingest_rejects_case_variant_connectivity_status(client, report_payload, connectivity_status):
    # Literal["online", "offline"] is an exact, case-sensitive match, so any
    # case variation is rejected even though the value is "obviously" valid
    # to a human reader.
    payload = report_payload(connectivity_status=connectivity_status)

    response = client.post("/reports", json=payload)

    assert response.status_code == 422


def test_ingest_accepts_arbitrarily_long_station_id_and_firmware_version(client, report_payload):
    # ReportIn only enforces min_length=1 on station_id/firmware_version -
    # there's no max_length, so nothing here stops a client from sending
    # values large enough to bloat storage or break assumptions elsewhere
    # (e.g. URL length limits on a real reverse proxy, even though this
    # in-process TestClient has no such limit to trip over).
    long_value = "A" * 3000
    payload = report_payload(station_id=long_value, firmware_version=long_value)

    post_response = client.post("/reports", json=payload)
    assert post_response.status_code == 201

    status_response = client.get(f"/stations/{long_value}/status")
    assert status_response.status_code == 200
    assert status_response.json()["firmware_version"] == long_value
