import pytest

from app.scoring import FLAGGING_THRESHOLD, compute_hygiene_score, is_flagged


class TestComputeHygieneScore:
    def test_perfect_report_scores_100(self):
        assert compute_hygiene_score("online", latency_ms=0, error_count=0) == 100.0

    def test_offline_alone_lands_exactly_on_threshold(self):
        score = compute_hygiene_score("offline", latency_ms=0, error_count=0)
        assert score == 60.0
        assert is_flagged(score) is False  # threshold is exclusive

    def test_one_point_below_threshold_is_flagged(self):
        score = compute_hygiene_score("offline", latency_ms=20, error_count=0)
        assert score == 59.0
        assert is_flagged(score) is True

    @pytest.mark.parametrize(
        "error_count,expected_penalty",
        [
            (0, 0.0),
            (1, 5.0),
            (5, 25.0),
            (6, 30.0),  # cap boundary
            (7, 30.0),  # just over cap, still capped
            (1000, 30.0),  # extreme, still capped
        ],
    )
    def test_error_penalty_caps_at_30(self, error_count, expected_penalty):
        score = compute_hygiene_score("online", latency_ms=0, error_count=error_count)
        assert score == pytest.approx(100.0 - expected_penalty)

    @pytest.mark.parametrize(
        "latency_ms,expected_penalty",
        [
            (0, 0.0),
            (100, 5.0),
            (399, 19.95),
            (400, 20.0),  # cap boundary
            (401, 20.0),  # just over cap, still capped
            (1_000_000, 20.0),  # extreme, still capped
        ],
    )
    def test_latency_penalty_caps_at_20(self, latency_ms, expected_penalty):
        score = compute_hygiene_score("online", latency_ms=latency_ms, error_count=0)
        assert score == pytest.approx(100.0 - expected_penalty)

    def test_worst_case_combination_floors_at_10_not_0(self):
        # Max possible penalty is 40 + 30 + 20 = 90, so under the current caps
        # the score can never actually reach the function's 0.0 floor -
        # documenting that max(score, 0.0) is defensive/unreachable in practice.
        score = compute_hygiene_score("offline", latency_ms=999_999, error_count=999_999)
        assert score == 10.0

    def test_non_offline_status_is_not_penalized(self):
        # compute_hygiene_score itself doesn't validate connectivity_status -
        # that's enforced by the API's Pydantic schema (Literal["online","offline"]).
        # Any value other than the exact string "offline" is treated as online.
        online = compute_hygiene_score("online", latency_ms=0, error_count=0)
        other = compute_hygiene_score("garbage", latency_ms=0, error_count=0)
        assert online == other == 100.0

    def test_score_is_rounded_to_two_decimals(self):
        # 7 / 20 = 0.35 exactly, so this exercises the round(..., 2) call
        # without relying on float-precision edge cases.
        score = compute_hygiene_score("online", latency_ms=7, error_count=0)
        assert score == pytest.approx(99.65)


class TestIsFlagged:
    def test_threshold_itself_is_not_flagged(self):
        assert is_flagged(FLAGGING_THRESHOLD) is False

    def test_just_below_threshold_is_flagged(self):
        assert is_flagged(FLAGGING_THRESHOLD - 0.01) is True

    def test_perfect_score_is_not_flagged(self):
        assert is_flagged(100.0) is False

    def test_zero_score_is_flagged(self):
        assert is_flagged(0.0) is True
