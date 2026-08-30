# Test Strategy — NOC Station Health API


## 1. Approach

Four layers:

**Unit** (`tests/unit/`) — `scoring.py` is the only pure, dependency-free logic, so it gets the deepest coverage: example-based tests pin the exact 60-point threshold (exclusive), both penalty caps at their boundaries, and the fact the `max(score, 0.0)` floor is unreachable (worst case is 10.0). Hypothesis property tests add invariants (bounds, monotonicity) across generated inputs for near-zero extra cost.

**Integration** (`tests/integration/`) — FastAPI `TestClient` + isolated per-test SQLite (§3). Covers validation, persistence/retrieval ordering, `/metrics/summary` aggregation, disallowed methods, and the `SIMULATED_LATENCY_MS` middleware (floor-only timing assertion). Heaviest-weighted layer — most real defects live at these seams, not inside the one pure function.

**Contract** (`tests/contract/`) — one guard comparing a *reduced* extraction of the OpenAPI schema (paths, methods, status codes, required fields + types) against a snapshot, deliberately not a raw diff (too brittle to version churn). Verified by simulating a real field rename and confirming it fails.

**E2E** (`tests/e2e/`, 5 tests) — smoke checks, one full round trip, one concurrency probe against a live instance. The only tier that saw real environment differences: 10 concurrent writes took ~12.6s locally (SQLite) vs. 0.67s for the *entire* suite in Docker (Postgres).

**Left out:** load/stress tooling, dashboard UI tests, and auth tests — the service has no auth layer.


## 2. Tool choices

- **pytest** — fixtures, parametrization, marks; no other runner needed.
- **FastAPI `TestClient` (httpx)** — in-process, fast, still exercises real routing/validation/middleware.
- **SQLAlchemy + isolated SQLite** — real ORM/SQL runs in every test without needing a live DB for most of the suite.
- **Hypothesis** — only for `scoring.py`, where it's pure and cheap; not used on the stateful API layer.
- **pytest-cov** — always visible (`--cov-report=term-missing`), but the `--cov-fail-under` gate lives only in CI, not local defaults — a narrow local run shouldn't fail on unrelated coverage.
- **Docker Compose** — an overlay adds a `tests` container onto the service's own compose file, reproducing CI locally under the same Python 3.11 runtime as production.


## 3. Test data strategy

Every unit/integration test gets its own SQLite file in `tmp_path`, wired in via `dependency_overrides` — no shared state, no cleanup code, real `noc.db` never touched. A `report_payload` factory builds valid payloads overridable per test.

E2E tests share the live service's real database, so isolation comes from uniqueness (`uuid4` station IDs) rather than resets, and assertions never touch global counts.

The contract snapshot is itself test data — a committed golden file, regenerated deliberately via `generate_snapshot.py`.


## 4. CI/CD integration

`.github/workflows/ci.yml` runs two required jobs on every push/PR:

1. **`fast-tests`** — Python 3.11, no Docker: unit + integration + contract, `--cov-fail-under=90`. Feedback in under a minute.
2. **`full-stack-tests`** — the validated `docker compose ... up --build --abort-on-container-exit` command, running everything including e2e against real Postgres. Also well under a minute, so it runs on every PR rather than nightly.

Split into two jobs so fast feedback doesn't wait on image builds.


## 5. Gaps & future work

-  Approach is feature-centric, need more redesigning when considering it in the whole business-flow.
- **4 confirmed defects are pinned as `xfail(strict=True)`**, not silently accepted: the `MAX(timestamp)` + join-back pattern duplicates a station's entry in `/stations`, `/stations/poor-hygiene`, and `/metrics/summary` on identical timestamps; a `station_id` containing `/` ingests but 404s on read. `strict=True` means a fix flips these to a failing "unexpected pass."
- `models.py`'s `datetime.utcnow()` default triggers a deprecation warning and will break on a future version — untested.
- No pagination on `/stations`; untested at scale. A lightweight load test (e.g. sustained `POST /reports` throughput, or `/stations` response time as the table grows) would be the natural next step — worth doing before this service sees real traffic.
- Only `/` is covered as a special character in `station_id`; others (spaces, `%`, non-ASCII) aren't.
- Timestamps only tested in UTC.
- The e2e concurrency probe uses a fixed n=10, not a sweep to find where contention actually starts failing.
- The 90% coverage threshold is a starting point (current baseline: 95%, with well-understood gaps in `get_db()` and the middleware's sleep branch), not a rigorously derived number.
