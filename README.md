# Station Health QA

This repo has two parts:

- [`service/`](service/) — the NOC Station Health API under test (FastAPI + SQLAlchemy).
- [`qa-automation-suite/`](qa-automation-suite/) — the test automation suite: unit, integration, contract, and end-to-end tests, plus `TEST_STRATEGY.md` and `AI_USAGE.md`.

See [`qa-automation-suite/README.md`](qa-automation-suite/README.md) for setup and run instructions.

CI runs on every push/PR via [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
