"""Regression tests for the synthetic RGC design simulation; no real cases are used."""

from __future__ import annotations

import runpy
from pathlib import Path
from random import Random
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SIMULATION: dict[str, Any] = runpy.run_path(str(ROOT / "scripts" / "simulate_rgc_design.py"))


def test_cohen_kappa_and_ac1_are_one_for_perfect_agreement() -> None:
    labels = [0, 1, 2, 3, 4]
    assert SIMULATION["kappa"](labels, labels) == 1.0
    assert SIMULATION["ac1"](labels, labels) == 1.0


def test_majority_label_tie_break_is_deterministic() -> None:
    labels = SIMULATION["LABELS"]
    assert SIMULATION["_majority_label"](["C1", "C0", "C1", "C0"]) == labels[0]


def test_synthetic_predictions_preserve_target_accuracy_under_independence() -> None:
    labels = SIMULATION["LABELS"]
    gold = [label for label in labels for _ in range(2_000)]

    predictions = SIMULATION["_system_predictions"](
        Random(20261021),
        gold,
        baseline_label="C0",
        system_accuracy=0.70,
        phi_target=0.0,
    )

    accuracy = sum(actual == predicted for actual, predicted in zip(gold, predictions, strict=True)) / len(gold)
    assert set(predictions) <= set(labels)
    assert abs(accuracy - 0.70) < 0.02
