from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ayorai_attractor.models import SearchRequest
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.providers.base import Provider, ProviderResponse


STATUS_MAP = {
    "verified": "VERIFIED",
    "supported": "SUPPORTED",
    "partially_supported": "PARTIALLY_SUPPORTED",
    "conflicting": "CONFLICTING",
    "unverified": "UNVERIFIED",
    "insufficient_evidence": "INSUFFICIENT_EVIDENCE",
    "failed": "FAILED",
}


class FixtureSearchProvider(Provider):
    """Closed-world, deterministic provider that returns only a case evidence pool."""

    id = "fixture-golden-v0"
    capabilities = frozenset({"search", "research", "evidence"})

    def __init__(self, documents: dict[str, dict[str, Any]], evidence_pool: list[str]) -> None:
        self.documents = documents
        self.evidence_pool = evidence_pool

    def execute(self, prompt: str) -> ProviderResponse:
        del prompt
        selected = [self.documents[doc_id] for doc_id in self.evidence_pool]
        excerpts = [str(doc["content"]) for doc in selected]
        source_ids = ",".join(str(doc["doc_id"]) for doc in selected)
        return ProviderResponse(
            text="\n\n".join(excerpts),
            source=f"fixture://golden-v0/{source_ids or 'empty'}",
            excerpt="\n\n".join(excerpts),
            independent=bool(selected),
        )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _accuracy(correct: int, total: int) -> dict[str, float | int]:
    return {
        "correct": correct,
        "total": total,
        "accuracy": round(correct / total, 6) if total else 0.0,
    }


def evaluate_golden_v0(
    golden_path: Path,
    corpus_path: Path,
) -> dict[str, Any]:
    cases = _load_jsonl(golden_path)
    corpus = _load_jsonl(corpus_path)
    documents = {str(doc["doc_id"]): doc for doc in corpus}

    results: list[dict[str, Any]] = []
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    category_totals: Counter[str] = Counter()
    category_correct: Counter[str] = Counter()
    state_totals: Counter[str] = Counter()
    state_correct: Counter[str] = Counter()
    expected_global = [
        str(case["global"])
        for case in cases
        if "global" in case
    ]

    majority_label = Counter(expected_global).most_common(1)[0][0]
    majority_correct = sum(label == majority_label for label in expected_global)

    abstain_total = 0
    abstain_correct = 0
    injection_total = 0
    injection_resistant = 0
    latencies_ms: list[float] = []

    for case in cases:
        evidence_pool = [str(doc_id) for doc_id in case.get("evidence_pool", [])]
        provider = FixtureSearchProvider(documents, evidence_pool)
        engine = Attractor(search_provider=provider)
        started = time.perf_counter()
        response = engine.run(
            SearchRequest(
                query=str(case["query"]),
                max_agents=5,
            )
        )
        latency_ms = (time.perf_counter() - started) * 1000
        latencies_ms.append(latency_ms)

        predicted = STATUS_MAP.get(response.verification.value, response.verification.value.upper())
        expected = case.get("global")
        expected_status = case.get("response_status")
        correct = bool(expected is not None and predicted == expected)

        if expected is not None:
            expected_label = str(expected)
            category = str(case["category"])
            category_totals[category] += 1
            state_totals[expected_label] += 1
            confusion[expected_label][predicted] += 1
            if correct:
                category_correct[category] += 1
                state_correct[expected_label] += 1

        if expected_status is not None:
            abstain_total += 1
            if expected_status.startswith("ABSTAIN/") and predicted == "UNVERIFIED":
                abstain_correct += 1

        if case.get("category") == "injection":
            injection_total += 1
            forbidden = [str(item).casefold() for item in case.get("must_not_follow", [])]
            answer = response.answer.casefold()
            if not any(token in answer for token in forbidden):
                injection_resistant += 1

        results.append(
            {
                "id": str(case["id"]),
                "category": str(case["category"]),
                "expected": expected,
                "expected_response_status": expected_status,
                "predicted": predicted,
                "correct": correct,
                "evidence_pool_size": len(evidence_pool),
                "latency_ms": round(latency_ms, 3),
            }
        )

    return {
        "suite": "golden-v0",
        "system": "current-attractor",
        "network": False,
        "case_count": len(cases),
        "corpus_document_count": len(corpus),
        "cases_with_global_verdict": len(expected_global),
        "abstain_cases": abstain_total,
        "majority_class_baseline": {
            "label": majority_label,
            **_accuracy(majority_correct, len(expected_global)),
        },
        "global_accuracy": _accuracy(
            sum(1 for result in results if result["correct"]),
            len(expected_global),
        ),
        "accuracy_by_category": {
            category: _accuracy(category_correct[category], category_totals[category])
            for category in sorted(category_totals)
        },
        "accuracy_by_state": {
            state: _accuracy(state_correct[state], state_totals[state])
            for state in sorted(state_totals)
        },
        "confusion_matrix": {
            expected: dict(sorted(predicted.items()))
            for expected, predicted in sorted(confusion.items())
        },
        "abstention_accuracy": _accuracy(abstain_correct, abstain_total),
        "injection_resistance": _accuracy(injection_resistant, injection_total),
        "latency_ms": {
            "p50": round(sorted(latencies_ms)[len(latencies_ms) // 2], 3),
            "p95": round(
                sorted(latencies_ms)[min(len(latencies_ms) - 1, int(len(latencies_ms) * 0.95))],
                3,
            ),
        },
        "results": results,
        "git_sha": os.getenv("GITHUB_SHA", "unknown"),
    }
