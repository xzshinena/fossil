import pytest

from ingest.compute_health_score import compute_health_score, normalize_series
from ingest.ingest_adzuna import _interpolate_monthly


# ── compute_health_score ──────────────────────────────────────────────────────

class TestComputeHealthScore:
    def test_all_sources_present(self):
        score, partial, breakdown = compute_health_score(80, 60, 40, 20)
        assert partial is False
        assert breakdown == {'github': 80.0, 'so': 60.0, 'jobs': 40.0, 'citations': 20.0}
        # Weighted: (80*.3 + 60*.25 + 40*.25 + 20*.2) / 1.0
        expected = round(80 * 0.30 + 60 * 0.25 + 40 * 0.25 + 20 * 0.20, 2)
        assert score == expected

    def test_all_sources_none_returns_none(self):
        score, partial, breakdown = compute_health_score(None, None, None, None)
        assert score is None
        assert partial is True
        assert breakdown == {}

    def test_one_source_missing_redistributes_weight(self):
        # Only github(0.30) and so(0.25) present — total weight = 0.55
        score, partial, breakdown = compute_health_score(100, 100, None, None)
        assert partial is True
        assert score == 100.0
        assert 'jobs' not in breakdown
        assert 'citations' not in breakdown

    def test_three_sources_missing(self):
        score, partial, breakdown = compute_health_score(50, None, None, None)
        assert partial is True
        assert score == 50.0
        assert breakdown == {'github': 50.0}

    def test_missing_one_source_weighted_correctly(self):
        # github=100, so=0, jobs=None, citations=None
        # available weight = 0.30 + 0.25 = 0.55
        # score = (100*0.30 + 0*0.25) / 0.55
        score, partial, _ = compute_health_score(100, 0, None, None)
        expected = round((100 * 0.30 + 0 * 0.25) / 0.55, 2)
        assert score == expected
        assert partial is True

    def test_score_clamped_to_100(self):
        score, _, _ = compute_health_score(100, 100, 100, 100)
        assert score == 100.0

    def test_score_clamped_to_0(self):
        score, _, _ = compute_health_score(0, 0, 0, 0)
        assert score == 0.0

    def test_score_rounded_to_2dp(self):
        score, _, _ = compute_health_score(33.333, 66.666, 50, 25)
        assert score == round(score, 2)
        assert isinstance(score, float)

    def test_breakdown_values_rounded(self):
        _, _, breakdown = compute_health_score(33.3333, 66.6666, None, None)
        for v in breakdown.values():
            assert v == round(v, 2)


# ── normalize_series ──────────────────────────────────────────────────────────

class TestNormalizeSeries:
    def test_normal_range(self):
        result = normalize_series([0, 50, 100])
        assert result == [0.0, 50.0, 100.0]

    def test_all_equal_returns_fifty(self):
        result = normalize_series([7, 7, 7])
        assert result == [50.0, 50.0, 50.0]

    def test_empty_returns_empty(self):
        assert normalize_series([]) == []

    def test_single_value_returns_fifty(self):
        assert normalize_series([42]) == [50.0]

    def test_min_max_scaling(self):
        result = normalize_series([10, 20, 30])
        assert result[0] == 0.0
        assert result[-1] == 100.0
        assert result[1] == 50.0

    def test_length_preserved(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert len(normalize_series(values)) == len(values)


# ── _interpolate_monthly ──────────────────────────────────────────────────────

class TestInterpolateMonthly:
    def test_single_year_all_months_equal(self):
        result = _interpolate_monthly({2020: 1000})
        assert len(result) == 12
        for month in range(1, 13):
            assert result[(2020, month)] == pytest.approx(1000.0, abs=1.0)

    def test_two_years_january_is_start_value(self):
        result = _interpolate_monthly({2020: 100, 2021: 200})
        assert result[(2020, 1)] == pytest.approx(100.0)

    def test_two_years_last_month_approaches_next(self):
        result = _interpolate_monthly({2020: 0, 2021: 120})
        # Month 12: progress = 11/12
        assert result[(2020, 12)] == pytest.approx(110.0, abs=1.0)

    def test_no_negative_values(self):
        result = _interpolate_monthly({2020: 100, 2021: 0})
        for val in result.values():
            assert val >= 0.0

    def test_covers_all_12_months(self):
        result = _interpolate_monthly({2022: 500, 2023: 600})
        for month in range(1, 13):
            assert (2022, month) in result
            assert (2023, month) in result

    def test_empty_input(self):
        assert _interpolate_monthly({}) == {}
