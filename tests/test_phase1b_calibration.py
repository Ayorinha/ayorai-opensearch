"""Synthetic-only tests for Phase 1b calibration; no benchmark records are used."""

from __future__ import annotations

import pytest

from scripts.benchmarks.phase1b.calibration import (
    calibrate_by_cohort,
    evaluate_metrics,
    make_frozen_threshold_artifact,
    predict_scores,
)


def test_threshold_grid_and_strict_greater_than() -> None:
    scores = [0.2, 0.3, 0.7, 0.8]
    labels = [0, 0, 1, 1]
    thresholds = calibrate_by_cohort(scores, labels, ["synthetic"] * 4)
    assert thresholds == {"synthetic": 0.31}
    predictions = predict_scores(
        [0.5, 0.50001], ["synthetic", "synthetic"], mode="fixed_0.5", split="dev"
    )
    assert predictions == [0, 1]


def test_threshold_tie_chooses_smallest_threshold() -> None:
    # All scores are equal; every grid threshold yields BA=0.5.
    assert calibrate_by_cohort([0.5] * 4, [0, 1, 0, 1], ["cohort"] * 4) == {
        "cohort": 0.01
    }


def test_calibrated_and_fixed_modes_are_distinct() -> None:
    scores = [0.2, 0.3, 0.7, 0.8]
    labels = [0, 0, 1, 1]
    threshold = calibrate_by_cohort(scores, labels, ["a"] * 4)["a"]
    artifact = make_frozen_threshold_artifact(
        model="synthetic-model",
        manifest_sha256="a" * 64,
        thresholds={"a": threshold},
    )
    fixed = predict_scores(
        [0.31], ["a"], mode="fixed_0.5", split="dev"
    )
    calibrated = predict_scores(
        [0.31], ["a"], mode="dev_calibrated_by_cohort", split="test",
        frozen_thresholds=artifact,
        model="synthetic-model",
        protocol=artifact["protocol"],
        manifest_sha256="a" * 64,
    )
    assert fixed == [0]
    assert calibrated == [1]


def test_test_split_requires_frozen_threshold_file() -> None:
    with pytest.raises(ValueError, match="frozen DEV threshold artifact"):
        predict_scores([0.8], ["cohort"], mode="fixed_0.5", split="test")


def test_test_split_rejects_provenance_mismatch() -> None:
    artifact = make_frozen_threshold_artifact(
        model="model-A", manifest_sha256="b" * 64, thresholds={"cohort": 0.5},
        mode="fixed_0.5",
    )
    with pytest.raises(ValueError, match="model mismatch"):
        predict_scores(
            [0.8], ["cohort"], mode="fixed_0.5", split="test",
            frozen_thresholds=artifact, model="model-B",
            protocol=artifact["protocol"], manifest_sha256="b" * 64,
        )


def test_metrics_report_global_macro_dataset_ragtruth_and_bootstrap() -> None:
    rows = [
        {"label": 0, "dataset": "synthetic-A"},
        {"label": 1, "dataset": "synthetic-A"},
        {"label": 0, "dataset": "RAGTruth"},
        {"label": 1, "dataset": "RAGTruth"},
    ]
    report = evaluate_metrics(rows, [0, 1, 1, 1], bootstrap_replicates=100, bootstrap_seed=7)
    assert report["balanced_accuracy_global"] == 0.75
    assert report["balanced_accuracy_macro_dataset"] == 0.75
    assert report["confusion_matrix_2x2"] == [[1, 1], [0, 2]]
    assert report["recall_by_class"] == {"0": 0.5, "1": 1.0}
    assert report["subsets"]["without_ragtruth"]["n"] == 2
    assert report["subsets"]["ragtruth_only"]["n"] == 2
    assert report["bootstrap"]["replicates"] == 100
    assert report["bootstrap"]["seed"] == 7


def test_single_class_cohort_fails_calibration_closed() -> None:
    with pytest.raises(ValueError, match="both classes"):
        calibrate_by_cohort([0.1, 0.2], [0, 0], ["one-class"] * 2)
