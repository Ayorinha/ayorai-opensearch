"""Synthetic tests for the preregistered DEV-A single-model selection rule."""

from __future__ import annotations

import pytest

from scripts.benchmarks.phase1b.calibration_v2.aggregate import select_single_model


def test_selection_uses_strict_less_than_point005_tie_band_and_cost() -> None:
    result = select_single_model(
        {"mdeberta": 0.800, "minicheck": 0.796, "factcg": None},
        costs={"mdeberta": 2.0, "minicheck": 1.0, "factcg": 3.0},
    )
    assert result["selected_model"] == "minicheck"
    assert result["tie_candidates"] == ["mdeberta", "minicheck"]
    assert result["ineligible_models"] == ["factcg"]


def test_exact_point005_difference_is_not_a_tie() -> None:
    result = select_single_model(
        {"mdeberta": 0.800, "minicheck": 0.795, "factcg": None},
        costs={"mdeberta": 2.0, "minicheck": 1.0, "factcg": 3.0},
    )
    assert result["selected_model"] == "mdeberta"
    assert result["tie_candidates"] == ["mdeberta"]


def test_all_candidates_ineligible_fails_closed() -> None:
    with pytest.raises(ValueError, match="no eligible"):
        select_single_model({"mdeberta": None, "minicheck": None, "factcg": None})


def test_calibration_v2_requires_exact_candidate_set() -> None:
    with pytest.raises(ValueError, match="exactly"):
        select_single_model({"mdeberta": 0.8, "minicheck": 0.7})
