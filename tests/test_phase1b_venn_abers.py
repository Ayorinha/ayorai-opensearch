"""Synthetic-only tests for the Venn-Abers reference implementation."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.benchmarks.phase1b.calibration_v2.venn_abers import venn_abers_reference


def test_reference_adds_both_hypothetical_labels() -> None:
    result = venn_abers_reference([0.0, 1.0], [0, 1], [0.5])
    assert result["p0"].tolist() == [0.0]
    assert result["p1"].tolist() == [1.0]
    assert result["p"].tolist() == [0.5]


def test_reference_handles_tied_calibration_and_query_scores() -> None:
    result = venn_abers_reference([0.0, 0.5, 0.5, 1.0], [0, 0, 1, 1], [0.5])
    assert result["p0"][0] <= result["p1"][0]
    assert 0.0 <= result["p"][0] <= 1.0


def test_reference_handles_queries_outside_calibration_range() -> None:
    result = venn_abers_reference([0.0, 1.0], [0, 1], [-10.0, 10.0])
    assert np.all(result["p0"] <= result["p1"])
    assert np.all((result["p"] >= 0.0) & (result["p"] <= 1.0))


def test_reference_randomized_invariant_and_probability_formula() -> None:
    rng = np.random.default_rng(20261107)
    score_grid = np.asarray([-2.0, -1.0, 0.0, 0.0, 0.5, 1.0, 2.0])
    for _ in range(300):
        n = int(rng.integers(2, 40))
        calibration_scores = rng.choice(score_grid, size=n, replace=True)
        calibration_labels = rng.integers(0, 2, size=n, dtype=np.int8)
        query_scores = rng.choice(
            np.asarray([-5.0, -2.0, -1.0, 0.0, 0.5, 1.0, 2.0, 5.0]),
            size=8,
            replace=True,
        )
        result = venn_abers_reference(calibration_scores, calibration_labels, query_scores)
        assert np.all(result["p0"] <= result["p1"])
        expected = result["p1"] / (1.0 - result["p0"] + result["p1"])
        np.testing.assert_allclose(result["p"], expected, rtol=0.0, atol=1e-12)


@pytest.mark.parametrize(
    ("scores", "labels", "queries"),
    [
        ([], [], [0.5]),
        ([0.1], [0], []),
        ([0.1, 0.2], [0], [0.5]),
        ([0.1, float("nan")], [0, 1], [0.5]),
        ([0.1, 0.2], [0, 2], [0.5]),
    ],
)
def test_reference_rejects_invalid_inputs(scores, labels, queries) -> None:
    with pytest.raises(ValueError):
        venn_abers_reference(scores, labels, queries)

def test_crossfit_is_out_of_fold_and_does_not_use_held_out_label() -> None:
    from scripts.benchmarks.phase1b.calibration_v2.venn_abers import ivap_crossfit

    scores = np.asarray([index % 7 for index in range(30)], dtype=np.float64)
    labels = np.asarray([index % 2 for index in range(30)], dtype=np.int8)
    folds = np.asarray([index % 5 for index in range(30)], dtype=np.int64)
    target = 7
    original = ivap_crossfit(scores, labels, folds)

    changed_labels = labels.copy()
    changed_labels[target] = 1 - changed_labels[target]
    changed = ivap_crossfit(scores, changed_labels, folds)

    assert original["p0"][target] == changed["p0"][target]
    assert original["p1"][target] == changed["p1"][target]
    assert original["p"][target] == changed["p"][target]
    assert np.all(original["p0"] <= original["p1"])


def test_crossfit_is_deterministic() -> None:
    from scripts.benchmarks.phase1b.calibration_v2.venn_abers import ivap_crossfit

    scores = np.asarray([index % 9 for index in range(40)], dtype=np.float64)
    labels = np.asarray([index % 2 for index in range(40)], dtype=np.int8)
    folds = np.asarray([index % 5 for index in range(40)], dtype=np.int64)
    first = ivap_crossfit(scores, labels, folds)
    second = ivap_crossfit(scores, labels, folds)
    for key in ("p0", "p1", "p"):
        np.testing.assert_array_equal(first[key], second[key])


def test_mondrian_marks_small_cohort_unavailable_without_fallback() -> None:
    from scripts.benchmarks.phase1b.calibration_v2.venn_abers import (
        ivap_crossfit_mondrian,
    )

    small_n = 150
    large_n = 250
    n = small_n + large_n
    scores = np.asarray([index % 11 for index in range(n)], dtype=np.float64)
    labels = np.asarray([index % 2 for index in range(n)], dtype=np.int8)
    folds = np.asarray([index % 5 for index in range(n)], dtype=np.int64)
    cohorts = np.asarray(["small"] * small_n + ["large"] * large_n)

    result = ivap_crossfit_mondrian(scores, labels, folds, cohorts)
    small = cohorts == "small"
    large = cohorts == "large"

    assert result["cohort_status"]["small"]["status"] == "mondrian_unavailable"
    assert result["cohort_status"]["small"]["minimum_calibration_n"] == 120
    assert np.all(result["status"][small] == "mondrian_unavailable")
    assert np.isnan(result["p"][small]).all()

    assert result["cohort_status"]["large"]["status"] == "available"
    assert result["cohort_status"]["large"]["minimum_calibration_n"] == 200
    assert np.all(result["status"][large] == "available")
    assert np.isfinite(result["p"][large]).all()
    assert np.all(result["p0"][large] <= result["p1"][large])


def test_mondrian_crossfit_is_deterministic() -> None:
    from scripts.benchmarks.phase1b.calibration_v2.venn_abers import (
        ivap_crossfit_mondrian,
    )

    n = 210
    scores = np.asarray([index % 13 for index in range(n)], dtype=np.float64)
    labels = np.asarray([index % 2 for index in range(n)], dtype=np.int8)
    folds = np.asarray([index % 5 for index in range(n)], dtype=np.int64)
    cohorts = np.asarray(["one_cohort"] * n)
    first = ivap_crossfit_mondrian(scores, labels, folds, cohorts)
    second = ivap_crossfit_mondrian(scores, labels, folds, cohorts)
    for key in ("p0", "p1", "p"):
        np.testing.assert_array_equal(first[key], second[key])
    np.testing.assert_array_equal(first["status"], second["status"])
