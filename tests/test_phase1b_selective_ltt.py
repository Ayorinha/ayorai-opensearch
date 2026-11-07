"""Synthetic-only tests for pre-registered selective Learn then Test."""

from __future__ import annotations

from fractions import Fraction
from math import comb

import pytest

from scripts.benchmarks.phase1b.calibration_v2.selective_ltt import (
    COHORT_ALPHA,
    THRESHOLDS,
    _binomial_lower_tail_pvalue,
    learn_then_test,
)


def _exact_binomial_cdf(errors: int, n: int) -> Fraction:
    return sum(
        (
            Fraction(comb(n, k), 1) * Fraction(1, 10) ** k * Fraction(9, 10) ** (n - k)
            for k in range(errors + 1)
        ),
        Fraction(0, 1),
    )


@pytest.mark.parametrize(
    ("n", "errors"),
    [(n, errors) for n in range(1, 13) for errors in range(n + 1)],
)
def test_log_binomial_matches_exact_fraction_sum(n: int, errors: int) -> None:
    actual = _binomial_lower_tail_pvalue(errors, n)
    expected = float(_exact_binomial_cdf(errors, n))
    assert actual == pytest.approx(expected, rel=1e-12, abs=1e-15)


def test_fixed_sequence_stops_at_first_non_rejection() -> None:
    result = learn_then_test(
        [1.0] * 25,
        [0] * 25,
        ["cohort"] * 25,
        partition="dev_b",
        split="dev",
        calibration_fit="dev_a_full",
    )["results"]["cohort"]

    assert result["status"] == "not_certified"
    assert result["tested_thresholds"] == [0.99]
    assert result["curve"][0]["decision"] == "not_rejected"
    assert all(point["decision"] == "descriptive" for point in result["curve"][1:])
    assert result["certified_threshold"] is None


def test_n_below_25_makes_cohort_ineligible_and_stops_sequence() -> None:
    result = learn_then_test(
        [1.0] * 24,
        [1] * 24,
        ["cohort"] * 24,
        partition="dev_b",
        split="dev",
        calibration_fit="dev_a_full",
    )["results"]["cohort"]

    assert result["status"] == "not_certified"
    assert result["tested_thresholds"] == []
    assert result["curve"][0]["decision"] == "ineligible_min_accepted"
    assert result["stop_reason"] == "n_below_25; sequence_stopped"
    assert all(point["decision"] == "descriptive" for point in result["curve"][1:])


def test_neutral_probability_is_supported_at_threshold_point_five() -> None:
    result = learn_then_test(
        [0.5] * 30,
        [1] * 30,
        ["cohort"] * 30,
        partition="dev_b",
        split="dev",
        calibration_fit="dev_a_full",
    )["results"]["cohort"]

    final_point = result["curve"][-1]
    assert final_point["threshold"] == 0.50
    assert final_point["n_accepted"] == 30
    assert final_point["errors"] == 0
    assert final_point["accuracy"] == 1.0


def test_successful_sequence_certifies_smallest_rejected_threshold() -> None:
    result = learn_then_test(
        [1.0] * 100,
        [1] * 100,
        ["cohort"] * 100,
        partition="dev_b",
        split="dev",
        calibration_fit="dev_a_full",
    )["results"]["cohort"]

    assert result["status"] == "certified"
    assert result["certified_threshold"] == 0.50
    assert result["tested_thresholds"] == list(THRESHOLDS)
    assert all(point["decision"] == "rejected" for point in result["curve"])
    assert result["alpha_cohort"] == pytest.approx(0.05 / 11)


def test_no_cohort_is_certified_when_all_predictions_are_wrong() -> None:
    result = learn_then_test(
        [1.0] * 25,
        [0] * 25,
        ["cohort"] * 25,
        partition="dev_b",
        split="dev",
        calibration_fit="dev_a_full",
    )
    assert all(
        cohort_result["status"] == "not_certified" for cohort_result in result["results"].values()
    )


def test_curve_has_all_thresholds_and_descriptive_points_after_stop() -> None:
    result = learn_then_test(
        [1.0] * 25,
        [0] * 25,
        ["cohort"] * 25,
        partition="dev_b",
        split="dev",
        calibration_fit="dev_a_full",
    )["results"]["cohort"]

    assert [point["threshold"] for point in result["curve"]] == list(THRESHOLDS)
    assert result["curve"][0]["decision"] == "not_rejected"
    assert all(point["p_value"] is None for point in result["curve"][1:])
    assert result["aurc"] == pytest.approx(0.0)


@pytest.mark.parametrize("partition", ["dev_a", "test", "DEV-B", ""])
def test_rejects_any_partition_other_than_dev_b(partition: str) -> None:
    with pytest.raises(ValueError, match="partition='dev_b'"):
        learn_then_test(
            [0.9] * 25,
            [1] * 25,
            ["cohort"] * 25,
            partition=partition,
            split="dev",
            calibration_fit="dev_a_full",
        )


def test_rejects_test_split() -> None:
    with pytest.raises(ValueError, match="TEST is forbidden"):
        learn_then_test(
            [0.9] * 25,
            [1] * 25,
            ["cohort"] * 25,
            partition="dev_b",
            split="test",
            calibration_fit="dev_a_full",
        )


def test_cohort_alpha_is_bonferroni_adjusted_for_eleven_cohorts() -> None:
    assert COHORT_ALPHA == pytest.approx(0.05 / 11)


def test_rejects_dev_a_crossfit_probabilities_as_certification_input() -> None:
    with pytest.raises(ValueError, match="fitted on all DEV-A"):
        learn_then_test(
            [0.9] * 25,
            [1] * 25,
            ["cohort"] * 25,
            partition="dev_b",
            split="dev",
            calibration_fit="dev_a_crossfit",
        )


def test_aurc_uses_trapezoids_over_observed_positive_coverages() -> None:
    probabilities = [1.0] * 25 + [0.6] * 25
    labels = [1] * 25 + [0] * 25
    result = learn_then_test(
        probabilities,
        labels,
        ["cohort"] * 50,
        partition="dev_b",
        split="dev",
        calibration_fit="dev_a_full",
    )["results"]["cohort"]

    assert result["curve"][0]["coverage"] == pytest.approx(0.5)
    assert result["curve"][THRESHOLDS.index(0.60)]["coverage"] == pytest.approx(1.0)
    assert result["aurc"] == pytest.approx(0.125)


def test_sequence_preserves_last_rejected_threshold_before_stopping() -> None:
    probabilities = [1.0] * 100 + [0.98] * 25
    labels = [1] * 100 + [0] * 25
    result = learn_then_test(
        probabilities,
        labels,
        ["cohort"] * 125,
        partition="dev_b",
        split="dev",
        calibration_fit="dev_a_full",
    )["results"]["cohort"]

    assert result["tested_thresholds"] == [0.99, 0.98]
    assert result["curve"][0]["decision"] == "rejected"
    assert result["curve"][1]["decision"] == "not_rejected"
    assert result["certified_threshold"] == 0.99
    assert all(point["decision"] == "descriptive" for point in result["curve"][2:])
