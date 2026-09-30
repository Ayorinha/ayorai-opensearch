#!/usr/bin/env python3
"""Lint the closed-world Golden v0 contract without executing the ATTRACTOR."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


def normalize_question(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def verdict_signature(case: dict[str, Any]) -> tuple[Any, ...]:
    claims = tuple(
        claim.get("verdict") for claim in case.get("expected_claims", [])
    )
    return (
        case.get("expected_verdict"),
        case.get("global"),
        claims,
        case.get("response_status"),
    )


def lint_golden(golden_path: Path, corpus_path: Path) -> list[str]:
    errors: list[str] = []
    golden = [
        json.loads(line)
        for line in golden_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    corpus = [
        json.loads(line)
        for line in corpus_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    corpus_ids = {doc.get("doc_id") for doc in corpus}

    seen_ids: set[str] = set()
    by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for case in golden:
        case_id = case.get("id")
        if not case_id:
            errors.append("case without id")
            continue
        if case_id in seen_ids:
            errors.append(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)

        if "evidence_pool" not in case:
            errors.append(f"{case_id}: missing evidence_pool")
            pool: list[str] = []
        else:
            pool = case["evidence_pool"]
            if not isinstance(pool, list):
                errors.append(f"{case_id}: evidence_pool must be a list")
                pool = []

        for doc_id in pool:
            if doc_id not in corpus_ids:
                errors.append(
                    f"{case_id}: evidence_pool references missing document {doc_id}"
                )

        for doc_id in case.get("must_cite", []):
            if doc_id not in pool:
                errors.append(
                    f"{case_id}: must_cite document {doc_id} is outside evidence_pool"
                )

        if not pool and not str(case.get("response_status", "")).startswith("ABSTAIN/"):
            errors.append(
                f"{case_id}: evidence_pool is empty but case is not ABSTAIN"
            )

        question = case.get("query")
        if isinstance(question, str):
            by_question[normalize_question(question)].append(case)

    for normalized, cases in by_question.items():
        signatures = {verdict_signature(case) for case in cases}
        if len(signatures) <= 1:
            continue

        for case in cases:
            contrast = case.get("contrast_with")
            if not contrast:
                errors.append(
                    f"{case['id']}: normalized question has differing gold labels "
                    f"without contrast_with (question={normalized!r})"
                )
            elif (
                not isinstance(contrast, list)
                or not contrast
                or not all(isinstance(item, str) for item in contrast)
            ):
                errors.append(
                    f"{case['id']}: contrast_with must be a non-empty list of case ids"
                )

    if len(golden) != 34:
        errors.append(f"expected 34 golden cases, found {len(golden)}")
    if len(corpus) != 52:
        errors.append(f"expected 52 corpus documents, found {len(corpus)}")

    missing_locales = [
        doc.get("doc_id") for doc in corpus if not doc.get("locale")
    ]
    if missing_locales:
        errors.append(
            f"documents missing locale: {', '.join(map(str, missing_locales))}"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--golden",
        type=Path,
        default=Path("evals/golden/v0.jsonl"),
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("evals/corpus/documents.jsonl"),
    )
    args = parser.parse_args()
    errors = lint_golden(args.golden, args.corpus)

    if errors:
        print("GOLDEN_LINT: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("GOLDEN_LINT: PASS")
    print("cases=34 corpus_documents=52 evidence_pools=34")
    print("duplicate_question_gold_conflicts=0")
    print("missing_evidence_pool_documents=0")
    print("empty_evidence_pool_non_abstain=0")
    print("missing_document_locale=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
