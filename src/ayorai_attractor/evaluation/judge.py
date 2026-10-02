"""Deterministic Judge evaluation over explicit structured fixtures."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ayorai_attractor.verification.judge import judge
from ayorai_attractor.verification.models import Claim, Evidence, StanceEdge


def evaluate_judge_suite(path: Path) -> dict[str, Any]:
    """Evaluate explicit Claim/Evidence/Stance fixtures without an LLM."""
    cases = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    results: list[dict[str, Any]] = []
    confusion: Counter[tuple[str, str]] = Counter()

    for case in cases:
        claim = Claim.model_validate(case["claim"])
        evidence = [Evidence.model_validate(item) for item in case["evidence"]]
        stances = [StanceEdge.model_validate(item) for item in case["stances"]]
        judgments, verdict = judge([claim], evidence, stances)
        predicted = verdict.value.upper()
        expected = str(case["expected"])
        confusion[(expected, predicted)] += 1
        results.append(
            {
                "id": str(case["id"]),
                "expected": expected,
                "predicted": predicted,
                "correct": predicted == expected,
                "claim_verdict": judgments[0].verdict.value.upper(),
            }
        )

    correct = sum(1 for item in results if item["correct"])
    return {
        "suite": "judge-v0",
        "case_count": len(results),
        "correct": correct,
        "accuracy": round(correct / len(results), 6) if results else 0.0,
        "confusion_matrix": {
            expected: {
                predicted: count
                for (gold, predicted), count in sorted(confusion.items())
                if gold == expected
            }
            for expected in sorted({gold for gold, _ in confusion})
        },
        "results": results,
    }
