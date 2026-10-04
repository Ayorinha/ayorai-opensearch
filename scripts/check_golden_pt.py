#!/usr/bin/env python3
"""Validate the schema and values of a Portuguese Golden JSONL file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "id",
    "claim",
    "source_id",
    "source_url",
    "source_excerpt",
    "justification",
    "annotator",
    "source_license",
    "label",
    "difficulty",
}
LABELS = {
    "VERIFIED",
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONFLICTING",
    "UNVERIFIED",
    "REFUTED",
}
DIFFICULTIES = {
    "numero",
    "data",
    "negacao",
    "parafrase",
    "apoio_parcial",
    "entidade_trocada",
}
TEXT_FIELDS = {
    "id",
    "claim",
    "source_id",
    "source_url",
    "source_excerpt",
    "justification",
    "annotator",
}


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"arquivo: não foi possível ler: {exc}"]

    if not lines:
        return ["arquivo: nenhum caso encontrado"]

    for line_number, raw_line in enumerate(lines, start=1):
        try:
            case = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            errors.append(f"linha {line_number}: JSON inválido: {exc.msg}")
            continue

        if not isinstance(case, dict):
            errors.append(f"linha {line_number}: caso deve ser um objeto JSON")
            continue

        fields = set(case)
        missing = sorted(REQUIRED_FIELDS - fields)
        extra = sorted(fields - REQUIRED_FIELDS)
        for field in missing:
            errors.append(f"linha {line_number}: campo faltando: {field}")
        for field in extra:
            errors.append(f"linha {line_number}: campo extra: {field}")

        for field in TEXT_FIELDS & fields:
            if not _nonempty_text(case[field]):
                errors.append(
                    f"linha {line_number}: valor inválido em {field}: texto não vazio esperado"
                )

        if "source_license" in case:
            license_value = case["source_license"]
            if not _nonempty_text(license_value) or license_value == "unknown":
                errors.append(
                    f"linha {line_number}: valor inválido em source_license: "
                    'texto não vazio diferente de "unknown" esperado'
                )

        if "label" in case and (not isinstance(case["label"], str) or case["label"] not in LABELS):
            errors.append(f"linha {line_number}: valor inválido em label: {case['label']!r}")

        if "difficulty" in case:
            difficulty = case["difficulty"]
            if (
                not isinstance(difficulty, list)
                or not difficulty
                or any(not isinstance(item, str) or item not in DIFFICULTIES for item in difficulty)
            ):
                errors.append(f"linha {line_number}: valor inválido em difficulty: {difficulty!r}")

        if "id" in case and _nonempty_text(case["id"]):
            case_id = case["id"]
            if case_id in seen_ids:
                errors.append(f"linha {line_number}: id repetido: {case_id!r}")
            else:
                seen_ids.add(case_id)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="caminho do arquivo JSONL")
    args = parser.parse_args()

    errors = validate(args.path)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
