from hypothesis import assume, given
from hypothesis import strategies as st

from app.scoring import FLAGGING_THRESHOLD, compute_hygiene_score, is_flagged

# error_count/latency_ms are unbounded >=0 in the schema (only ge=0 is
# enforced), so these strategies deliberately include very large values -
# the same territory that surfaced the "0.0 floor is unreachable" finding
# in test_scoring.py.
latencies = st.floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False)
error_counts = st.integers(min_value=0, max_value=1_000_000)
known_statuses = st.sampled_from(["online", "offline"])
arbitrary_statuses = st.text(max_size=20)


@given(status=known_statuses, latency_ms=latencies, error_count=error_counts)
def test_score_is_always_within_0_and_100(status, latency_ms, error_count):
    score = compute_hygiene_score(status, latency_ms, error_count)
    assert 0.0 <= score <= 100.0


@given(status=known_statuses, latency_ms=latencies, error_count=error_counts)
def test_score_never_has_more_than_two_decimal_places(status, latency_ms, error_count):
    score = compute_hygiene_score(status, latency_ms, error_count)
    assert score == round(score, 2)


@given(status=known_statuses, latency_ms=latencies, e1=error_counts, e2=error_counts)
def test_more_errors_never_improves_the_score(status, latency_ms, e1, e2):
    fewer, more = sorted((e1, e2))
    score_fewer = compute_hygiene_score(status, latency_ms, fewer)
    score_more = compute_hygiene_score(status, latency_ms, more)
    assert score_more <= score_fewer


@given(status=known_statuses, error_count=error_counts, l1=latencies, l2=latencies)
def test_more_latency_never_improves_the_score(status, error_count, l1, l2):
    lower, higher = sorted((l1, l2))
    score_lower = compute_hygiene_score(status, lower, error_count)
    score_higher = compute_hygiene_score(status, higher, error_count)
    assert score_higher <= score_lower


@given(latency_ms=latencies, error_count=error_counts)
def test_offline_is_never_scored_better_than_online(latency_ms, error_count):
    offline_score = compute_hygiene_score("offline", latency_ms, error_count)
    online_score = compute_hygiene_score("online", latency_ms, error_count)
    assert offline_score <= online_score


@given(status=arbitrary_statuses, latency_ms=latencies, error_count=error_counts)
def test_any_non_offline_string_scores_identically_to_online(status, latency_ms, error_count):
    # compute_hygiene_score only special-cases the exact string "offline" -
    # everything else, including nonsense input, is treated as online. That's
    # enforced elsewhere by the API schema, not by this function itself.
    assume(status != "offline")
    online_score = compute_hygiene_score("online", latency_ms, error_count)
    other_score = compute_hygiene_score(status, latency_ms, error_count)
    assert other_score == online_score


@given(status=known_statuses, latency_ms=latencies, error_count=error_counts)
def test_is_flagged_matches_the_documented_threshold(status, latency_ms, error_count):
    score = compute_hygiene_score(status, latency_ms, error_count)
    assert is_flagged(score) == (score < FLAGGING_THRESHOLD)
