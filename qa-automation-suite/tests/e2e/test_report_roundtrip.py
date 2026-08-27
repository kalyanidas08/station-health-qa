def test_ingest_report_is_retrievable_over_real_http(api_client, report_payload):
    # penalty: latency 100/20=5, errors 2*5=10 -> 100 - 15 = 85
    payload = report_payload(latency_ms=100, error_count=2)

    post_response = api_client.post("/reports", json=payload)
    assert post_response.status_code == 201
    assert post_response.json()["hygiene_score"] == 85.0

    status_response = api_client.get(f"/stations/{payload['station_id']}/status")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["hygiene_score"] == 85.0
    assert body["flagged"] is False
    assert body["firmware_version"] == payload["firmware_version"]
