#!/usr/bin/env python3
"""Validate the schema and values of a Portuguese Golden JSONL file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ayorai_attractor.verification.excerpt import locate_excerpt

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


def _read_corpus(path: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    errors: list[str] = []
    corpus: dict[str, dict[str, str]] = {}
    required_fields = {
        "source_id",
        "source_url",
        "source_license",
        "retrieved_at",
        "text",
    }

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {}, [f"corpus: não foi possível ler: {exc}"]

    for line_number, raw_line in enumerate(lines, start=1):
        try:
            source = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            errors.append(f"corpus linha {line_number}: JSON inválido: {exc.msg}")
            continue

        if not isinstance(source, dict):
            errors.append(
                f"corpus linha {line_number}: documento deve ser um objeto JSON"
            )
            continue

        fields = set(source)
        missing = sorted(required_fields - fields)
        extra = sorted(fields - required_fields)
        for field in missing:
            errors.append(f"corpus linha {line_number}: campo faltando: {field}")
        for field in extra:
            errors.append(f"corpus linha {line_number}: campo extra: {field}")

        invalid_text = [
            field
            for field in required_fields & fields
            if not _nonempty_text(source[field])
        ]
        for field in sorted(invalid_text):
            errors.append(
                f"corpus linha {line_number}: valor inválido em {field}: "
                "texto não vazio esperado"
            )

        if "source_license" in source and (
            not _nonempty_text(source["source_license"])
            or source["source_license"] == "unknown"
        ):
            errors.append(
                f'corpus linha {line_number}: valor inválido em source_license: '
                'texto não vazio diferente de "unknown" esperado'
            )

        source_id = source.get("source_id")
        source_is_valid = (
            _nonempty_text(source_id)
            and not missing
            and not extra
            and not invalid_text
            and source.get("source_license") != "unknown"
        )
        if _nonempty_text(source_id) and source_id in corpus:
            errors.append(
                f"corpus linha {line_number}: source_id repetido: {source_id!r}"
            )
        elif source_is_valid:
            corpus[source_id] = source

    return corpus, errors


def validate(path: Path, corpus_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    corpus: dict[str, dict[str, str]] = {}
    if corpus_path is not None:
        corpus, corpus_errors = _read_corpus(corpus_path)
        errors.extend(corpus_errors)
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

        if corpus_path is not None and "source_id" in case:
            source_id = case["source_id"]
            if _nonempty_text(source_id):
                source = corpus.get(source_id)
                if source is None:
                    errors.append(
                        f"linha {line_number}: source_id não encontrado no corpus: "
                        f"{source_id!r}"
                    )
                else:
                    if case.get("source_url") != source["source_url"]:
                        errors.append(
                            f"linha {line_number}: source_url diferente da fonte "
                            f"do corpus para {source_id!r}"
                        )
                    if case.get("source_license") != source["source_license"]:
                        errors.append(
                            f"linha {line_number}: source_license diferente da fonte "
                            f"do corpus para {source_id!r}"
                        )
                    excerpt = case.get("source_excerpt")
                    if _nonempty_text(excerpt) and locate_excerpt(
                        source["text"], excerpt
                    ) is None:
                        errors.append(
                            f"linha {line_number}: source_excerpt não encontrado "
                            f"na fonte do corpus para {source_id!r}"
                        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="caminho do arquivo JSONL")
    parser.add_argument("--corpus", type=Path, help="arquivo JSONL do corpus de fontes")
    args = parser.parse_args()

    errors = validate(args.path, args.corpus)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
