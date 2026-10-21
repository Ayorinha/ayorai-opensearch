#!/usr/bin/env python3
"""Calculate inter-annotator agreement for the proposed RGC PT-BR label set."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from collections.abc import Sequence
from pathlib import Path
from random import Random
from typing import Any

LABELS = (
    "SUPPORTED",
    "REFUTED",
    "UNVERIFIED",
    "PARTIALLY_SUPPORTED",
    "CONFLICTING",
)
RULE_GAP = "RULE_GAP"
SEED = 20261003


def _read_annotations(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"arquivo: não foi possível ler: {exc}") from exc

    annotations: dict[str, str] = {}
    for line_number, raw_line in enumerate(lines, start=1):
        try:
            record: Any = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"linha {line_number}: JSON inválido: {exc.msg}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"linha {line_number}: caso deve ser um objeto JSON")
        case_id = record.get("id")
        label = record.get("label")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"linha {line_number}: id textual não vazio é obrigatório")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"linha {line_number}: label textual não vazio é obrigatório")
        if case_id in annotations:
            raise ValueError(f"linha {line_number}: id repetido: {case_id!r}")
        annotations[case_id] = label
    return annotations


def _kappa_for_labels(a: Sequence[str], b: Sequence[str]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    n = len(a)
    observed = sum(left == right for left, right in zip(a, b, strict=True)) / n
    counts_a = Counter(a)
    counts_b = Counter(b)
    expected = sum(
        (counts_a[label] / n) * (counts_b[label] / n) for label in LABELS
    )
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def calculate_kappa(a: dict[str, str], b: dict[str, str]) -> tuple[int, float, list[str]]:
    """Backward-compatible point estimate for aligned annotation files."""
    if set(a) != set(b):
        raise ValueError("os conjuntos de ids são diferentes")
    ids = sorted(a)
    kappa = _kappa_for_labels([a[key] for key in ids], [b[key] for key in ids])
    if kappa is None:
        raise ZeroDivisionError
    disagreements = [case_id for case_id in ids if a[case_id] != b[case_id]]
    return len(ids), kappa, disagreements


def calculate_agreement(
    a: dict[str, str],
    b: dict[str, str],
    *,
    iterations: int = 10_000,
) -> dict[str, Any]:
    """Return unweighted Cohen's kappa, percentile CI, and descriptive counts."""
    if set(a) != set(b):
        raise ValueError("os conjuntos de ids são diferentes")
    if iterations < 1:
        raise ValueError("iterations deve ser >= 1")
    for case_id, label in [*a.items(), *b.items()]:
        if label not in LABELS and label != RULE_GAP:
            raise ValueError(f"rótulo inválido em {case_id!r}: {label!r}")

    ids = sorted(a)
    excluded = [case_id for case_id in ids if a[case_id] == RULE_GAP or b[case_id] == RULE_GAP]
    included = [case_id for case_id in ids if case_id not in set(excluded)]
    if not included:
        raise ValueError("nenhum caso elegível após excluir RULE_GAP")

    left = [a[case_id] for case_id in included]
    right = [b[case_id] for case_id in included]
    kappa = _kappa_for_labels(left, right)
    observed = sum(x == y for x, y in zip(left, right, strict=True)) / len(included)
    matrix = {gold: {pred: 0 for pred in LABELS} for gold in LABELS}
    for gold, pred in zip(left, right, strict=True):
        matrix[gold][pred] += 1

    rng = Random(SEED)
    bootstrap: list[float] = []
    for _ in range(iterations):
        indices = [rng.randrange(len(included)) for _ in included]
        value = _kappa_for_labels(
            [left[index] for index in indices],
            [right[index] for index in indices],
        )
        if value is not None:
            bootstrap.append(value)
    bootstrap.sort()
    ci95: list[float] | None = None
    if bootstrap:
        ci95 = [
            bootstrap[int(0.025 * (len(bootstrap) - 1))],
            bootstrap[int(0.975 * (len(bootstrap) - 1))],
        ]

    return {
        "n_included": len(included),
        "n_rule_gap_excluded": len(excluded),
        "rule_gap_case_ids": excluded,
        "cohen_kappa_unweighted": kappa,
        "kappa_ci95_percentile": ci95,
        "bootstrap_valid_replicates": len(bootstrap),
        "bootstrap_iterations": iterations,
        "bootstrap_seed": SEED,
        "observed_agreement": observed,
        "confusion_matrix": matrix,
        "label_counts_annotator_a": dict(Counter(left)),
        "label_counts_annotator_b": dict(Counter(right)),
        "gate_threshold": 0.6,
        "gate_passed": kappa is not None and kappa >= 0.6,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotator_a", type=Path, help="JSONL do anotador A")
    parser.add_argument("annotator_b", type=Path, help="JSONL do anotador B")
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--out", type=Path, help="arquivo JSON de saída opcional")
    args = parser.parse_args()

    try:
        a = _read_annotations(args.annotator_a)
        b = _read_annotations(args.annotator_b)
        report = calculate_agreement(a, b, iterations=args.iterations)
    except (ValueError, ZeroDivisionError) as exc:
        print(str(exc) or "kappa indefinido", file=sys.stderr)
        return 1

    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out is None:
        print(serialized, end="")
    else:
        args.out.write_text(serialized, encoding="utf-8")
        print(f"relatório escrito: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
