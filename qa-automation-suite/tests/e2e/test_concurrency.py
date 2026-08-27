import concurrent.futures


def test_concurrent_reports_for_same_station_all_succeed(api_client, unique_station_id, report_payload):
    """Fires simultaneous POST /reports for the same station over real HTTP.

    The README notes local SQLite and Dockerized Postgres "behave differently
    under concurrent load." Locally (SQLite) this can surface write-contention
    failures (e.g. "database is locked"); against Postgres it should hold up
    cleanly. This test doesn't assume which environment it's running against -
    it documents the difference by simply reporting what actually happened.
    """
    payloads = [
        report_payload(timestamp=f"2024-06-01T10:00:{i:02d}Z", error_count=i) for i in range(10)
    ]

    def _post(payload):
        return api_client.post("/reports", json=payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(_post, payloads))

    status_codes = [r.status_code for r in responses]
    assert status_codes == [201] * len(payloads), (
        f"Expected all {len(payloads)} concurrent writes to return 201; got {status_codes}. "
        "If this is running locally against SQLite, this may fail under write "
        "contention - see TEST_STRATEGY.md for the SQLite-vs-Postgres concurrency note."
    )
