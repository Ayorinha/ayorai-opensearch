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
    assert thresholds == {"synthetic": 0.3}
    predictions = predict_scores(
        [0.5, 0.50001], ["synthetic", "synthetic"], mode="fixed_0.5", split="dev"
    )
    assert predictions == [0, 1]


def test_threshold_tie_chooses_smallest_threshold() -> None:
    # All scores are equal; every grid threshold yields BA=0.5.
    assert calibrate_by_cohort([0.5] * 4, [0, 1, 0, 1], ["cohort"] * 4) == {"cohort": 0.01}


def test_calibrated_and_fixed_modes_are_distinct() -> None:
    scores = [0.2, 0.3, 0.7, 0.8]
    labels = [0, 0, 1, 1]
    threshold = calibrate_by_cohort(scores, labels, ["a"] * 4)["a"]
    artifact = make_frozen_threshold_artifact(
        model="synthetic-model",
        manifest_sha256="a" * 64,
        thresholds={"a": threshold},
    )
    fixed = predict_scores([0.4], ["a"], mode="fixed_0.5", split="dev")
    calibrated = predict_scores(
        [0.4],
        ["a"],
        mode="dev_calibrated_by_cohort",
        split="test",
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
        model="model-A",
        manifest_sha256="b" * 64,
        thresholds={"cohort": 0.5},
        mode="fixed_0.5",
    )
    with pytest.raises(ValueError, match="model mismatch"):
        predict_scores(
            [0.8],
            ["cohort"],
            mode="fixed_0.5",
            split="test",
            frozen_thresholds=artifact,
            model="model-B",
            protocol=artifact["protocol"],
            manifest_sha256="b" * 64,
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


def test_vectorised_bootstrap_matches_naive_case_bootstrap_in_distribution() -> None:
    import random

    np = pytest.importorskip("numpy")
    from scripts.benchmarks.phase1b.calibration import _bootstrap_ci, balanced_accuracy

    labels = [1] * 60 + [0] * 40
    predictions = [1] * 45 + [0] * 15 + [0] * 30 + [1] * 10
    fast = _bootstrap_ci(labels, predictions, metric="balanced_accuracy", replicates=4000)
    rng = random.Random(7)
    naive = []
    for _ in range(4000):
        idx = [rng.randrange(100) for _ in range(100)]
        ys = [labels[i] for i in idx]
        ps = [predictions[i] for i in idx]
        if 0 < sum(ys) < 100:
            naive.append(balanced_accuracy(ys, ps))
    low, high = np.percentile(naive, [2.5, 97.5])
    assert abs(fast["lower"] - low) < 0.02
    assert abs(fast["upper"] - high) < 0.02
    assert fast["valid_replicates"] + fast["undefined_replicates"] == 4000


def test_bootstrap_is_deterministic_and_reports_stratified_macro_ci() -> None:
    pytest.importorskip("numpy")
    rows = [{"label": i % 2, "dataset": "A" if i < 40 else "B"} for i in range(80)]
    predictions = [(i % 2) if i % 5 else 1 - (i % 2) for i in range(80)]
    first = evaluate_metrics(rows, predictions, bootstrap_replicates=500)
    second = evaluate_metrics(rows, predictions, bootstrap_replicates=500)
    assert first["bootstrap"] == second["bootstrap"]
    macro_ci = first["bootstrap"]["macro_dataset_balanced_accuracy_ci95"]
    assert macro_ci["method"] == "stratified_by_dataset_case_bootstrap"
    assert macro_ci["lower"] <= first["balanced_accuracy_macro_dataset"] <= macro_ci["upper"]
