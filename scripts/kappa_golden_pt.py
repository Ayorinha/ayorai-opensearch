#!/usr/bin/env python3
"""Calculate Cohen's kappa for two annotator Golden JSONL files."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


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


def calculate_kappa(a: dict[str, str], b: dict[str, str]) -> tuple[int, float, list[str]]:
    if set(a) != set(b):
        raise ValueError("os conjuntos de ids são diferentes")

    ids = list(a)
    n = len(ids)
    disagreements = [case_id for case_id in ids if a[case_id] != b[case_id]]
    po = sum(a[case_id] == b[case_id] for case_id in ids) / n if n else 1.0

    counts_a = Counter(a.values())
    counts_b = Counter(b.values())
    labels = set(counts_a) | set(counts_b)
    pe = sum(
        (counts_a[label] / n) * (counts_b[label] / n)
        for label in labels
    ) if n else 1.0

    if pe == 1:
        raise ZeroDivisionError

    kappa = (po - pe) / (1 - pe)
    return n, kappa, disagreements


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("annotator_a", type=Path, help="JSONL do anotador A")
    parser.add_argument("annotator_b", type=Path, help="JSONL do anotador B")
    args = parser.parse_args()

    try:
        a = _read_annotations(args.annotator_a)
        b = _read_annotations(args.annotator_b)
        n, kappa, disagreements = calculate_kappa(a, b)
    except ZeroDivisionError:
        print("kappa indefinido")
        return 2
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"n: {n}")
    print(f"kappa: {kappa:.3f}")
    print(f"divergências: {disagreements}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
