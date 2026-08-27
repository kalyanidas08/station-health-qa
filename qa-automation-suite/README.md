# QA Automation Suite — NOC Station Health API

A test automation suite for the NOC Station Health API (the FastAPI service in the sibling `service/` directory). See [`TEST_STRATEGY.md`](TEST_STRATEGY.md) for the reasoning behind the approach, and [`AI_USAGE.md`](AI_USAGE.md) for how AI tools were used while building it.

## Layout

```
qa-automation-suite/
├── tests/
│   ├── unit/          # scoring.py logic: example-based + Hypothesis property tests
│   ├── integration/   # API tests via FastAPI TestClient + isolated SQLite per test
│   ├── contract/      # OpenAPI schema regression guard
│   └── e2e/           # real HTTP against an already-running instance
├── conftest.py         # shared fixtures (isolated DB, TestClient, report payload factory)
├── pytest.ini
├── requirements-test.txt
├── Dockerfile                  # test-runner image (built with repo root as context - see below)
└── docker-compose.test.yml     # overlay on service/docker-compose.yml, adds a `tests` service
```

This suite expects `service/` to exist as a **sibling directory** (`../service` relative to this folder) — `pytest.ini` adds it to `pythonpath` so tests can `import app`.

## Prerequisites

- Python 3.11 (matches the service's own `Dockerfile`; other 3.x versions generally work too — see the note below)
- Docker Desktop (or another Docker Compose v2 setup), only needed for `tests/e2e` and the full containerized run

> **Note on Python versions:** `requirements-test.txt` deliberately excludes `psycopg2-binary` (see `TEST_STRATEGY.md` §2 for why), so it installs cleanly on newer Python versions too (this suite was also developed against 3.14 locally). CI and the Docker test runner both use 3.11 for parity with the service's production runtime.

## Setup

```powershell
cd qa-automation-suite
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
```

## Running the tests

### Fast tests — unit, integration, contract (no Docker needed)

These run entirely in-process against an isolated SQLite database; no live server required.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit tests/integration tests/contract --cov=app --cov-report=term-missing
```

### End-to-end tests — requires a live, already-running instance

Start the service first, either locally:

```powershell
cd ../service
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

or via Docker (real Postgres + the documented 40ms simulated latency):

```powershell
cd ../service
docker compose up -d
```

Then, from `qa-automation-suite/`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/e2e
```

If no service is reachable at `http://localhost:8000`, these tests skip cleanly (they don't fail the run) — see `tests/e2e/conftest.py`. Point them at a different instance with the `E2E_BASE_URL` environment variable.

### Full suite in a container (recommended — matches CI exactly)

Runs the entire suite, including `tests/e2e`, inside a container against the real Dockerized Postgres stack:

```powershell
cd ..   # repo root
docker compose -f service/docker-compose.yml -f qa-automation-suite/docker-compose.test.yml `
  up --build --abort-on-container-exit --exit-code-from tests tests
```

**Afterward, tear the stack down explicitly** — `--abort-on-container-exit` stops the `tests` container on completion but leaves `db`/`api` running:

```powershell
docker compose -f service/docker-compose.yml -f qa-automation-suite/docker-compose.test.yml down
```

**Viewing the HTML report:** this run also produces a self-contained HTML test report, bind-mounted out of the container to `qa-automation-suite/test-reports/report.html` the moment the run finishes — just open that file directly in a browser, no server needed. (The path is deliberately expressed relative to `service/`, which is Compose's default project directory for bind-mount resolution when `service/docker-compose.yml` is the first `-f` file — see the comment in `docker-compose.test.yml` if you ever change the file order.)

## Coverage

`pytest-cov` is always wired in for visibility (`--cov=app --cov-report=term-missing`), but no coverage threshold is enforced by default locally — running a single narrow test file shouldn't fail on coverage of code that file was never meant to touch. The hard gate (`--cov-fail-under=90`) is applied only in CI, on the full fast-tests run. See `TEST_STRATEGY.md` §5 for the current coverage baseline and known, deliberate gaps.

## Updating the API contract snapshot

If you make an intentional, reviewed change to a request/response schema or endpoint, regenerate the contract snapshot and commit the diff so reviewers can see exactly what changed for API consumers:

```powershell
.\.venv\Scripts\python.exe tests\contract\generate_snapshot.py
```

## CI

`.github/workflows/ci.yml` runs two jobs on every push/PR to `main`: `fast-tests` (unit + integration + contract, coverage-gated) and `full-stack-tests` (the full suite, containerized, against real Postgres). Both are required checks.
