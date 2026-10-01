"""Reproducible system comparison primitives for R10."""

from dataclasses import dataclass


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
