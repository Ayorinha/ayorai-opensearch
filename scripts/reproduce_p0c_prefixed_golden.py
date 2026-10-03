#!/usr/bin/env python3
"""Reproduce the pre-fix P0 claim-pipeline Golden v0 result.

This script intentionally freezes the observed pre-fix configuration. It is a
diagnostic artifact, not a benchmark target. Golden v0 is treated as DEV after
this point; do not tune production rules against these cases.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ayorai_attractor.evaluation.golden import evaluate_golden_v0
from ayorai_attractor.evaluation.stats import mcnemar_exact_pvalue
from ayorai_attractor.verification.claim_pipeline import (
    ClaimVerificationPipeline,
    RuleScopeClassifier,
)
from ayorai_attractor.verification.extraction import RetrievedDocument, RuleClaimExtractor
from ayorai_attractor.verification.stance import RuleStanceDetector

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "evals/golden/v0.jsonl"
CORPUS = ROOT / "evals/corpus/documents.jsonl"
RETRIEVED_AT = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
OUT_OF_SCOPE_TERMS = ("diagnóstico", "diagnostico", "estratégia jurídica", "estrategia juridica")


def load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class FixtureRetriever:
    def __init__(self, documents: dict[str, dict[str, object]], evidence_pool: list[str]) -> None:
        self.documents = documents
        self.evidence_pool = evidence_pool

    def retrieve(self, query: str) -> list[RetrievedDocument]:
        del query
        output: list[RetrievedDocument] = []
        for document_id in self.evidence_pool:
            item = self.documents[document_id]
            content = str(item["content"])
            output.append(
                RetrievedDocument(
                    id=document_id,
                    content=content,
                    source_id=document_id,
                    source_location=str(item["url"]),
                    retrieved_at=datetime.fromisoformat(
                        str(item.get("retrieved_at", RETRIEVED_AT.isoformat())).replace("Z", "+00:00")
                    ),
                    end_offset=len(content),
                    origin_id=str(item["origin_id"]),
                    canonical_url=str(item["url"]),
                )
            )
        return output


def main() -> None:
    cases = load_jsonl(GOLDEN)
    corpus = {
        str(item["doc_id"]): item
        for item in load_jsonl(CORPUS)
    }
    legacy = evaluate_golden_v0(GOLDEN, CORPUS)
    legacy_by_id = {item["id"]: item["predicted"] for item in legacy["results"]}

    pipeline_predictions: dict[str, str] = {}
    expected: list[str] = []
    legacy_labels: list[str] = []
    pipeline_labels: list[str] = []

    for case in cases:
        if "global" not in case:
            continue
        case_id = str(case["id"])
        expected_label = str(case["global"]).upper()
        evidence_pool = [str(item) for item in case.get("evidence_pool", [])]
        pipeline = ClaimVerificationPipeline(
            retriever=FixtureRetriever(corpus, evidence_pool),
            claim_extractor=RuleClaimExtractor(),
            stance_detector=RuleStanceDetector(),
            scope_classifier=RuleScopeClassifier(forbidden_terms=OUT_OF_SCOPE_TERMS),
        )
        result = pipeline.verify(str(case["query"]))
        predicted = (
            result.verdict.value.upper()
            if result.verdict is not None
            else result.status.value.upper().replace("/", "_")
        )
        pipeline_predictions[case_id] = predicted
        expected.append(expected_label)
        legacy_labels.append(str(legacy_by_id[case_id]).upper())
        pipeline_labels.append(predicted)

    correct = sum(gold == predicted for gold, predicted in zip(expected, pipeline_labels, strict=True))
    legacy_correct = sum(gold == predicted for gold, predicted in zip(expected, legacy_labels, strict=True))
    legacy_right_new_wrong = sum(
        gold == old and gold != new
        for gold, old, new in zip(expected, legacy_labels, pipeline_labels, strict=True)
    )
    new_right_legacy_wrong = sum(
        gold != old and gold == new
        for gold, old, new in zip(expected, legacy_labels, pipeline_labels, strict=True)
    )
    p_value = mcnemar_exact_pvalue(expected, legacy_labels, pipeline_labels)

    print(f"pipeline_accuracy={correct}/{len(expected)}={correct / len(expected):.6f}")
    print(f"legacy_accuracy={legacy_correct}/{len(expected)}={legacy_correct / len(expected):.6f}")
    print(f"legacy_right_new_wrong={legacy_right_new_wrong}")
    print(f"new_right_legacy_wrong={new_right_legacy_wrong}")
    print(f"mcnemar_exact_p={p_value:.8f}")
    print("pipeline_predictions=" + json.dumps(pipeline_predictions, sort_keys=True))

    assert len(expected) == 30
    assert correct == 9
    assert legacy_correct == 13
    assert legacy_right_new_wrong == 6
    assert new_right_legacy_wrong == 2
    assert round(p_value, 8) == 0.28906250


if __name__ == "__main__":
    main()
