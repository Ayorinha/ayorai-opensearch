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
