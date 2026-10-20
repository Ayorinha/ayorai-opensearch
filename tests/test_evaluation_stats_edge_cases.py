from __future__ import annotations

import pytest

from ayorai_attractor.evaluation.stats import (
    balanced_accuracy,
    bootstrap_accuracy,
    confusion_matrix,
    mcnemar_exact_pvalue,
)


def test_confusion_matrix_conserves_every_observation() -> None:
    expected = ["SUPPORTED", "SUPPORTED", "REFUTED", "UNVERIFIED", "REFUTED"]
    predicted = ["SUPPORTED", "REFUTED", "REFUTED", "CONFLICTING", "SUPPORTED"]
    matrix = confusion_matrix(expected, predicted)
    assert sum(sum(row.values()) for row in matrix.values()) == len(expected)
    assert sum(matrix["SUPPORTED"].values()) == 2
    assert matrix["SUPPORTED"]["SUPPORTED"] == 1
    assert matrix["SUPPORTED"]["REFUTED"] == 1


@pytest.mark.parametrize(
    ("expected", "predicted"),
    [
        (["SUPPORTED"], []),
        ([], ["SUPPORTED"]),
        (["SUPPORTED", "REFUTED"], ["SUPPORTED"]),
    ],
)
def test_confusion_matrix_rejects_mismatched_lengths(
    expected: list[str], predicted: list[str]
) -> None:
    with pytest.raises(ValueError, match="same length"):
        confusion_matrix(expected, predicted)


@pytest.mark.parametrize(
    ("expected", "predicted"),
    [
        (["UNKNOWN"], ["SUPPORTED"]),
        (["SUPPORTED"], ["UNKNOWN"]),
    ],
)
def test_confusion_matrix_rejects_unknown_labels(expected: list[str], predicted: list[str]) -> None:
    with pytest.raises(ValueError, match="Judge verdict states"):
        confusion_matrix(expected, predicted)


def test_balanced_accuracy_is_one_for_perfect_predictions() -> None:
    labels = ["SUPPORTED", "SUPPORTED", "REFUTED", "UNVERIFIED"]
    assert balanced_accuracy(labels, labels) == 1.0


def test_balanced_accuracy_is_zero_when_each_present_class_is_missed() -> None:
    expected = ["SUPPORTED", "SUPPORTED", "REFUTED", "REFUTED"]
    predicted = ["REFUTED", "REFUTED", "SUPPORTED", "SUPPORTED"]
    assert balanced_accuracy(expected, predicted) == 0.0


def test_balanced_accuracy_ignores_classes_absent_from_gold() -> None:
    expected = ["SUPPORTED", "SUPPORTED", "REFUTED"]
    predicted = ["SUPPORTED", "REFUTED", "REFUTED"]
    # Recall(SUPPORTED)=1/2 and recall(REFUTED)=1; absent classes add no zeroes.
    assert balanced_accuracy(expected, predicted) == pytest.approx(0.75)


@pytest.mark.parametrize(
    ("expected", "predicted"),
    [
        ([], []),
        (["SUPPORTED"], []),
        ([], ["SUPPORTED"]),
    ],
)
def test_balanced_accuracy_rejects_empty_or_mismatched_inputs(
    expected: list[str], predicted: list[str]
) -> None:
    with pytest.raises(ValueError, match="non-empty and equal"):
        balanced_accuracy(expected, predicted)


def test_bootstrap_accuracy_bounds_for_perfect_and_failed_predictions() -> None:
    labels = ["SUPPORTED", "REFUTED", "UNVERIFIED"]
    assert bootstrap_accuracy(labels, labels, iterations=100, seed=17) == (1.0, 1.0)
    wrong = ["REFUTED", "UNVERIFIED", "SUPPORTED"]
    assert bootstrap_accuracy(labels, wrong, iterations=100, seed=17) == (0.0, 0.0)


@pytest.mark.parametrize(
    ("expected", "predicted", "iterations"),
    [
        (["SUPPORTED"], [], 100),
        ([], [], 100),
        (["SUPPORTED"], ["SUPPORTED"], 0),
        (["SUPPORTED"], ["SUPPORTED"], -1),
    ],
)
def test_bootstrap_accuracy_rejects_invalid_inputs(
    expected: list[str], predicted: list[str], iterations: int
) -> None:
    with pytest.raises(ValueError, match="invalid bootstrap inputs|same length"):
        bootstrap_accuracy(expected, predicted, iterations=iterations, seed=17)


def test_mcnemar_exact_probability_matches_small_known_cases() -> None:
    # With one discordant pair, the exact two-sided p-value is 1.
    gold = ["SUPPORTED"]
    first = ["SUPPORTED"]
    second = ["REFUTED"]
    assert mcnemar_exact_pvalue(gold, first, second) == 1.0

    # Four discordant pairs all favoring one system gives 2 / 2**4 = 0.125.
    gold = ["SUPPORTED"] * 4
    first = ["SUPPORTED"] * 4
    second = ["REFUTED"] * 4
    assert mcnemar_exact_pvalue(gold, first, second) == pytest.approx(0.125)


def test_mcnemar_is_symmetric_when_systems_are_swapped() -> None:
    gold = ["SUPPORTED", "SUPPORTED", "REFUTED", "REFUTED", "UNVERIFIED"]
    first = ["SUPPORTED", "REFUTED", "REFUTED", "SUPPORTED", "UNVERIFIED"]
    second = ["REFUTED", "SUPPORTED", "SUPPORTED", "REFUTED", "SUPPORTED"]
    assert mcnemar_exact_pvalue(gold, first, second) == mcnemar_exact_pvalue(gold, second, first)


def test_mcnemar_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="same length"):
        mcnemar_exact_pvalue(["SUPPORTED"], ["SUPPORTED"], [])
