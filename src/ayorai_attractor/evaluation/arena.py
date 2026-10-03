"""Comparable benchmark reporting without selecting a winning system."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from ayorai_attractor.evaluation.stats import (
    bootstrap_accuracy,
    confusion_matrix,
    mcnemar_exact_pvalue,
)


@dataclass(frozen=True)
class SystemEvaluation:
    system_id: str
    expected: tuple[str, ...]
    predicted: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.expected) != len(self.predicted):
            raise ValueError("expected and predicted must have the same length")

    @property
    def accuracy(self) -> float:
        if not self.expected:
            raise ValueError("at least one observation is required")
        return sum(
            gold == guess
            for gold, guess in zip(self.expected, self.predicted, strict=True)
        ) / len(self.expected)


@dataclass(frozen=True)
class ArenaReport:
    systems: tuple[SystemEvaluation, ...]
    bootstrap_intervals: dict[str, tuple[float, float]]
    confusion_matrices: dict[str, dict[str, dict[str, int]]]
    pairwise_mcnemar: dict[tuple[str, str], float]


def build_arena_report(
    systems: Sequence[SystemEvaluation],
    *,
    bootstrap_iterations: int = 10_000,
    bootstrap_seed: int = 20261003,
) -> ArenaReport:
    if not systems:
        raise ValueError("at least one system is required")
    ids = [system.system_id for system in systems]
    if len(ids) != len(set(ids)):
        raise ValueError("system_id values must be unique")

    intervals = {
        system.system_id: bootstrap_accuracy(
            system.expected,
            system.predicted,
            iterations=bootstrap_iterations,
            seed=bootstrap_seed,
        )
        for system in systems
    }
    matrices = {
        system.system_id: confusion_matrix(system.expected, system.predicted)
        for system in systems
    }
    pairwise: dict[tuple[str, str], float] = {}
    for index, left in enumerate(systems):
        for right in systems[index + 1 :]:
            if left.expected != right.expected:
                raise ValueError("paired systems must use identical expected labels")
            pairwise[(left.system_id, right.system_id)] = mcnemar_exact_pvalue(
                left.expected,
                left.predicted,
                right.predicted,
            )

    return ArenaReport(
        systems=tuple(systems),
        bootstrap_intervals=intervals,
        confusion_matrices=matrices,
        pairwise_mcnemar=pairwise,
    )
