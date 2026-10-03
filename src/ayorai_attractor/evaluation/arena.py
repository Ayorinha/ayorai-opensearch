"""Comparable, non-ranking evaluation arena primitives for R10."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ayorai_attractor.evaluation.stats import (
    bootstrap_accuracy,
    confusion_matrix,
    mcnemar_exact_pvalue,
)


@dataclass(frozen=True)
class SystemEvaluation:
    """Metrics for one system on one fixed ordered gold sequence."""

    system_id: str
    accuracy: float
    bootstrap_95_ci: tuple[float, float]
    confusion: dict[str, dict[str, int]]
    predictions: tuple[str, ...]


@dataclass(frozen=True)
class PairedComparison:
    """Paired statistical result without selecting a winner."""

    system_a: str
    system_b: str
    mcnemar_exact_pvalue: float


class EvaluationArena:
    """Evaluate systems on identical gold cases without ranking them."""

    def evaluate(
        self,
        expected: Sequence[str],
        predictions: dict[str, Sequence[str]],
        *,
        bootstrap_iterations: int = 10_000,
        seed: int = 20261003,
    ) -> tuple[SystemEvaluation, ...]:
        if not expected:
            raise ValueError("at least one expected label is required")
        if not predictions:
            raise ValueError("at least one system is required")

        results: list[SystemEvaluation] = []
        for system_id in sorted(predictions):
            observed = tuple(predictions[system_id])
            if len(observed) != len(expected):
                raise ValueError(
                    f"system {system_id!r} has a different number of predictions"
                )
            accuracy = sum(
                gold == guess
                for gold, guess in zip(expected, observed, strict=True)
            ) / len(expected)
            results.append(
                SystemEvaluation(
                    system_id=system_id,
                    accuracy=accuracy,
                    bootstrap_95_ci=bootstrap_accuracy(
                        expected,
                        observed,
                        iterations=bootstrap_iterations,
                        seed=seed,
                    ),
                    confusion=confusion_matrix(expected, observed),
                    predictions=observed,
                )
            )
        return tuple(results)

    def paired(
        self,
        expected: Sequence[str],
        evaluations: Sequence[SystemEvaluation],
    ) -> tuple[PairedComparison, ...]:
        comparisons: list[PairedComparison] = []
        ordered = sorted(evaluations, key=lambda item: item.system_id)
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                comparisons.append(
                    PairedComparison(
                        system_a=first.system_id,
                        system_b=second.system_id,
                        mcnemar_exact_pvalue=mcnemar_exact_pvalue(
                            expected,
                            first.predictions,
                            second.predictions,
                        ),
                    )
                )
        return tuple(comparisons)
