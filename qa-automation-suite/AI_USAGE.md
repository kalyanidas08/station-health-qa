# AI Usage

This suite was built through an interactive session with Claude (via Claude Code), file by file rather than from a single prompt. Every non-trivial output was verified by actually running it, not just described — and several proposals were modified or rejected along the way. Three examples of each follow.


## Example 1 — Accepted as-is

**Task given:** direction to scaffold the test project before writing any actual test cases — specifically, to make tests runnable in isolation without depending on a live server or touching the real database.

**Output:** Claude designed `conftest.py`'s `db_session`/`client` fixtures — a fresh SQLite file in `tmp_path` per test, wired in via FastAPI's `app.dependency_overrides[get_db]`. It also set `DATABASE_URL` to a disposable temp file before `app.main` even imports, since that import triggers `Base.metadata.create_all()` against the real default engine as a side effect.

**Why accepted without changes:** it worked correctly from the first test onward — no shared state, no manual cleanup, real `noc.db` never touched. It's also the most load-bearing code in the suite (all 60+ tests depend on it), so a subtle flaw would have silently invalidated results everywhere rather than failing loudly. None ever surfaced.



## Example 2 — Modified significantly

**Task given:** a chain of review rounds hardening the same growing suite: build a contract/schema guard, then "Request-shape/negative tests are thin...", then react to what those new tests found, then "I want an HTML report accessible in the local when tests completed in docker."

**1. Contract design — off-by-one path bug.** *Before:* `generate_snapshot.py` used `_HERE.parents[1] / "service"`, one level too shallow → `ModuleNotFoundError`. *After:* fixed to `parents[2]`, verified by rerunning and inspecting the generated snapshot.

**2. Negative test coverage — a real gap, called out directly.** *Before:* `test_reports.py`/`test_stations.py` covered the happy path plus basic validation, nothing on extra fields, case sensitivity, unbounded lengths, or special characters in `station_id`. *After:* four tests added; three confirmed safe behavior, but `test_station_id_with_slash_is_retrievable_via_status` — written expecting success — **failed** against the real service: a `station_id` containing `/` ingests fine but 404s on `GET /stations/{station_id}/status`, since the router reads the embedded `/` as an extra path segment. A genuine, previously unknown defect, found only because the gap was pointed out.

**3. Representing that defect — plain failure vs. `xfail`.** *Before:* the slash test was an unmarked assertion — would read as an unexplained red failure in every future CI run. *After:* marked `xfail(strict=True, reason="BUG: ...")`, matching the duplicate-timestamp defects' pattern, so it reads as a documented known issue instead of a broken test, and would flag itself if ever fixed.

**4. HTML report — Docker Compose path bug.** *Before:* `volumes: ./test-reports:/workspace/qa-automation-suite/test-reports`, described as done — but the file actually landed under `service/test-reports/`, not `qa-automation-suite/`. Compose resolves relative bind-mount paths against the *first* `-f` file's directory, not the file where `volumes:` is written. First fix attempt (`--project-directory .`) broke the image build instead. *After:* path rewritten relative to the actual default project directory (`../qa-automation-suite/test-reports:...`), verified by rerunning and checking the file on disk.



## Example 3 — Rejected outright

**What Claude suggested:** make `qa-automation-suite/` self-contained by copying the entire `service/` directory into it, on the assumption a standalone test repo shouldn't depend on files outside itself.

**Why it was wrong:** the actual plan was to push `service/` and `qa-automation-suite/` as siblings in one repo, not publish the test suite in isolation. Copying would have created two drifting copies of the same source for no benefit. Claude defaulted to a generic pattern without confirming what was actually being published; the user rejected the copy directly and said to leave `service/` where it is — `pytest.ini`'s `pythonpath = ../service` and the Docker build's `context: ..` were built around that sibling structure instead.
