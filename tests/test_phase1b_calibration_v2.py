"""Synthetic-only tests for deterministic V2 splits and probabilistic metrics."""

from __future__ import annotations

import math

import pytest

from scripts.benchmarks.phase1b.calibration_v2 import (
    crossfit_folds,
    probabilistic_metrics,
    split_dev_a_b,
)


def test_dev_split_is_deterministic_balanced_and_cohort_stratified() -> None:
    ids = [f"id-{index:02d}" for index in range(12)]
    cohorts = ["A"] * 5 + ["B"] * 7
    first, first_hash = split_dev_a_b(ids, cohorts)
    second, second_hash = split_dev_a_b(list(reversed(ids)), list(reversed(cohorts)))
    assert first == second
    assert first_hash == second_hash
    for cohort in ("A", "B"):
        members = [
            record_id
            for record_id, value in zip(ids, cohorts, strict=True)
            if value == cohort
        ]
        assigned = [first[record_id] for record_id in members]
        assert assigned.count("DEV-A") == math.ceil(len(members) / 2)
        assert assigned.count("DEV-B") == len(members) // 2


def test_split_hash_uses_canonical_sorted_mapping() -> None:
    import hashlib

    from scripts.benchmarks.phase1b.common import canonical_json

    mapping, digest = split_dev_a_b(["b", "a"], ["cohort", "cohort"])
    assert digest == hashlib.sha256(canonical_json(mapping)).hexdigest()


def test_crossfit_folds_are_deterministic_and_stratified() -> None:
    ids = [f"id-{index:02d}" for index in range(40)]
    cohorts = ["A"] * 20 + ["B"] * 20
    labels = [0, 1] * 10 + [0, 1] * 10
    first, limitations = crossfit_folds(ids, cohorts, labels)
    second, second_limitations = crossfit_folds(
        list(reversed(ids)), list(reversed(cohorts)), list(reversed(labels))
    )
    assert first == second
    assert limitations == second_limitations == []
    for cohort in ("A", "B"):
        for label in (0, 1):
            folds = [
                first[record_id]
                for record_id, row_cohort, row_label in zip(
                    ids, cohorts, labels, strict=True
                )
                if row_cohort == cohort and row_label == label
            ]
            assert sorted(folds) == sorted(position % 5 for position in range(len(folds)))


def test_crossfit_reports_strata_smaller_than_five_without_changing_fold_count() -> None:
    folds, limitations = crossfit_folds(["a", "b", "c", "d"], ["A"] * 4, [0] * 4)
    assert set(folds.values()) == {0, 1, 2, 3}
    assert limitations == [
        {"cohort": "A", "label": "0", "n": 4, "required_folds": 5}
    ]


def test_auroc_matches_naive_pairwise_mann_whitney_with_ties() -> None:
    probabilities = [0.2, 0.2, 0.8, 0.8, 0.5]
    labels = [0, 1, 1, 0, 1]
    result = probabilistic_metrics(probabilities, labels)
    positives = [p for p, y in zip(probabilities, labels, strict=True) if y == 1]
    negatives = [p for p, y in zip(probabilities, labels, strict=True) if y == 0]
    naive = sum(
        (positive > negative) + 0.5 * (positive == negative)
        for positive in positives
        for negative in negatives
    ) / (len(positives) * len(negatives))
    assert result["auroc"] == pytest.approx(naive)


def test_auprc_matches_naive_average_precision_stepwise() -> None:
    probabilities = [0.9, 0.8, 0.8, 0.1]
    labels = [1, 0, 1, 0]
    result = probabilistic_metrics(probabilities, labels)
    order = sorted(range(len(labels)), key=lambda index: probabilities[index], reverse=True)
    true_positives = 0
    naive = 0.0
    previous_recall = 0.0
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and probabilities[order[end]] == probabilities[order[index]]:
            end += 1
        true_positives += sum(labels[order[position]] for position in range(index, end))
        precision = true_positives / end
        recall = true_positives / sum(labels)
        naive += (recall - previous_recall) * precision
        previous_recall = recall
        index = end
    assert result["auprc"] == pytest.approx(naive)


def test_brier_log_loss_and_prevalence_match_naive_calculation() -> None:
    probabilities = [0.1, 0.8, 0.6, 0.4]
    labels = [0, 1, 0, 1]
    result = probabilistic_metrics(probabilities, labels)
    expected_brier = sum(
        (probability - label) ** 2
        for probability, label in zip(probabilities, labels, strict=True)
    ) / 4
    expected_log = -sum(
        label * math.log(max(1e-15, probability))
        + (1 - label) * math.log(max(1e-15, 1 - probability))
        for probability, label in zip(probabilities, labels, strict=True)
    ) / 4
    assert result["brier_score"] == pytest.approx(expected_brier)
    assert result["log_loss"] == pytest.approx(expected_log)
    assert result["prevalence"] == 0.5


def test_adaptive_ece_keeps_equal_probabilities_together() -> None:
    result = probabilistic_metrics([0.1] * 10 + [0.9] * 10, [0] * 10 + [1] * 10)
    bins = result["reliability_diagram"]
    assert len(bins) == 2
    assert [item["n"] for item in bins] == [10, 10]
    assert result["ece_bins_empty"] == 13


def test_single_class_marks_rank_metrics_undefined_explicitly() -> None:
    result = probabilistic_metrics([0.1, 0.2, 0.3], [0, 0, 0])
    assert result["auroc"] is None
    assert result["auprc"] is None
    assert result["auroc_auprc_status"] == "undefined_single_class"
    assert math.isfinite(result["brier_score"])
    assert math.isfinite(result["log_loss"])


def test_perfect_probabilities_have_zero_brier_and_log_loss_is_clipped() -> None:
    perfect = probabilistic_metrics([0.0, 1.0], [0, 1])
    assert perfect["brier_score"] == 0.0
    assert math.isfinite(perfect["log_loss"])
    assert perfect["log_loss"] > 0.0


def test_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError, match="equally sized"):
        probabilistic_metrics([0.2], [0, 1])
    with pytest.raises(ValueError, match="finite and in"):
        probabilistic_metrics([1.1], [1])
    with pytest.raises(ValueError, match="binary integers"):
        probabilistic_metrics([0.2], [2])
