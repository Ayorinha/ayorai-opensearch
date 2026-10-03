"""Reproducible system comparison primitives for R10."""

from dataclasses import dataclass
from collections.abc import Sequence

from ayorai_attractor.evaluation.stats import (
    bootstrap_accuracy,
    confusion_matrix,
    mcnemar_exact_pvalue,
)


@dataclass(frozen=True)
class ArenaCase:
    case_id: str
    expected: str


@dataclass(frozen=True)
class ArenaScore:
    system_id: str
    correct: int
    total: int
    accuracy: float


@dataclass(frozen=True)
class ArenaReport:
    scores: tuple[ArenaScore, ...]
    bootstrap_intervals: dict[str, tuple[float, float]]
    confusion_matrices: dict[str, dict[str, dict[str, int]]]
    pairwise_mcnemar: dict[tuple[str, str], float]


def score_system(
    system_id: str,
    cases: list[ArenaCase],
    predictions: dict[str, str],
) -> ArenaScore:
    if not cases:
        raise ValueError("arena requires at least one case")
    correct = sum(predictions.get(case.case_id) == case.expected for case in cases)
    return ArenaScore(
        system_id=system_id,
        correct=correct,
        total=len(cases),
        accuracy=correct / len(cases),
    )


def compare_systems(
    cases: Sequence[ArenaCase],
    predictions_by_system: dict[str, dict[str, str]],
    *,
    bootstrap_iterations: int = 10_000,
    bootstrap_seed: int = 20261003,
) -> ArenaReport:
    """Produce comparable statistics without selecting a winning system."""
    if not cases:
        raise ValueError("arena requires at least one case")
    if not predictions_by_system:
        raise ValueError("at least one system is required")

    expected = tuple(case.expected.upper() for case in cases)
    scores = tuple(
        score_system(system_id, list(cases), predictions)
        for system_id, predictions in predictions_by_system.items()
    )
    intervals = {}
    matrices = {}
    normalized_predictions: dict[str, tuple[str, ...]] = {}
    for system_id, predictions in predictions_by_system.items():
        labels = tuple(predictions.get(case.case_id, "").upper() for case in cases)
        if "" in labels:
            raise ValueError(f"missing prediction for system: {system_id}")
        normalized_predictions[system_id] = labels
        intervals[system_id] = bootstrap_accuracy(
            expected,
            labels,
            iterations=bootstrap_iterations,
            seed=bootstrap_seed,
        )
        matrices[system_id] = confusion_matrix(expected, labels)

    pairwise: dict[tuple[str, str], float] = {}
    ids = list(predictions_by_system)
    for index, left in enumerate(ids):
        for right in ids[index + 1 :]:
            pairwise[(left, right)] = mcnemar_exact_pvalue(
                expected,
                normalized_predictions[left],
                normalized_predictions[right],
            )
    return ArenaReport(
        scores=scores,
        bootstrap_intervals=intervals,
        confusion_matrices=matrices,
        pairwise_mcnemar=pairwise,
    )
