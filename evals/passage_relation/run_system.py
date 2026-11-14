"""Produce a passage-relation run of /v1/check for a frozen variant.

Runs only on a fully adjudicated, human-written case file (metrics.load_cases refuses
anything else). The run records the variant, the engine metadata reported by
check_documents and the SHA-256 of the case file, so a run cannot be scored against
other cases. Experimental variants are added to VARIANTS by their own reviewed change
and frozen (config recorded) before any evaluation case is run.

Usage:
    python -m evals.passage_relation.run_system --cases C --documents D --variant current --out R
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ayorai_attractor.verification.document_check import (
    CheckDocumentInput,
    DocumentCheckResult,
    check_documents,
)
from evals.passage_relation.metrics import (
    SCHEMA,
    EvaluationInputError,
    load_cases,
    load_documents,
    read_jsonl,
    sha256_file,
)

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)  # retrieved_at does not affect verdicts

Variant = Callable[[list[CheckDocumentInput], str], DocumentCheckResult]

VARIANTS: dict[str, Variant] = {
    "current": lambda documents, claim: check_documents(
        documents, claims=[claim], retrieved_at=FIXED_TIME
    ),
}


def run(cases_path: Path, documents_path: Path, variant: str) -> dict[str, Any]:
    if variant not in VARIANTS:
        raise EvaluationInputError(f"unknown variant {variant!r}; known: {sorted(VARIANTS)}")
    cases = load_cases(cases_path)
    documents = load_documents(documents_path)
    document_ids: Mapping[str, Sequence[str]] = {
        row["case_id"]: row.get("document_ids") or [] for row in read_jsonl(cases_path)
    }
    engine: dict[str, str] | None = None
    results = []
    for case_id in sorted(cases):
        ids = document_ids[case_id]
        if not ids or any(not isinstance(item, str) or item not in documents for item in ids):
            raise EvaluationInputError(f"{case_id}: document_ids must name known documents")
        inputs = [CheckDocumentInput(id=item, text=documents[item]) for item in ids]
        outcome = VARIANTS[variant](inputs, cases[case_id].claim)
        if engine is None:
            engine = dict(outcome.engine)
        elif dict(outcome.engine) != engine:
            raise EvaluationInputError("engine metadata changed during the run")
        (claim,) = outcome.results
        results.append(
            {
                "case_id": case_id,
                "verdict": claim.verdict,
                "evidence": [
                    {
                        "document_id": item.document_id,
                        "start": item.start,
                        "end": item.end,
                        "stance": item.stance,
                    }
                    for item in claim.evidence
                ],
            }
        )
    return {
        "schema": SCHEMA,
        "meta": {
            "variant": variant,
            "cases_sha256": sha256_file(cases_path),
            "documents_sha256": sha256_file(documents_path),
            "engine": engine or {},
        },
        "results": results,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run(args.cases, args.documents, args.variant)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(report['results'])} claims, variant {args.variant} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
