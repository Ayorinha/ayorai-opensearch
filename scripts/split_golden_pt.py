#!/usr/bin/env python3
"""Create a deterministic visible/hidden split from a Golden JSONL file."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

SEED = 20261003
HIDDEN_FRACTION = 0.3


def _read_cases(path: Path) -> list[tuple[str, str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError as exc:
        raise ValueError(f"arquivo: não foi possível ler: {exc}") from exc

    cases: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(lines, start=1):
        try:
            case: Any = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"linha {line_number}: JSON inválido: {exc.msg}") from exc
        if (
            not isinstance(case, dict)
            or not isinstance(case.get("id"), str)
            or not case["id"].strip()
        ):
            raise ValueError(f"linha {line_number}: id textual não vazio é obrigatório")
        case_id = case["id"]
        if case_id in seen:
            raise ValueError(f"linha {line_number}: id repetido: {case_id!r}")
        seen.add(case_id)
        cases.append((case_id, raw_line))
    return cases


def split_cases(input_path: Path, output_dir: Path) -> str:
    repo_root = Path(__file__).resolve().parents[1]
    resolved_output = output_dir.resolve()
    if resolved_output == repo_root or repo_root in resolved_output.parents:
        raise ValueError("pasta de saída dentro do repositório não é permitida")

    cases = _read_cases(input_path)
    ids = sorted(case_id for case_id, _ in cases)
    rng = random.Random(SEED)
    rng.shuffle(ids)
    hidden_count = round(HIDDEN_FRACTION * len(ids))
    hidden_ids = set(ids[:hidden_count])

    output_dir.mkdir(parents=True, exist_ok=True)
    hidden_path = output_dir / "hidden.jsonl"
    visible_path = output_dir / "visible.jsonl"

    hidden_path.write_text(
        "".join(raw_line for case_id, raw_line in cases if case_id in hidden_ids),
        encoding="utf-8",
    )
    visible_path.write_text(
        "".join(raw_line for case_id, raw_line in cases if case_id not in hidden_ids),
        encoding="utf-8",
    )
    return hashlib.sha256(hidden_path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="arquivo JSONL de entrada")
    parser.add_argument("output_dir", type=Path, help="pasta de saída")
    args = parser.parse_args()

    try:
        digest = split_cases(args.input, args.output_dir)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
