from __future__ import annotations

import hashlib
import json
import os
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from ayorai_attractor.evaluation.golden import (
    FixtureRetriever,
    _legacy_prediction,
    _load_jsonl,
)
from ayorai_attractor.evaluation.stats import (
    balanced_accuracy,
    bootstrap_accuracy,
    confusion_matrix,
    mcnemar_exact_pvalue,
)
from ayorai_attractor.verification.claim_pipeline import (
    ClaimVerificationPipeline,
    RuleScopeClassifier,
)
from ayorai_attractor.verification.nli import (
    EVAL_ONLY_LEVEL,
    EVAL_ONLY_MODEL,
    EVAL_ONLY_REVISION,
    TransformersNLIBackend,
)
from ayorai_attractor.verification.stance import (
    NLIStanceDetector,
    RuleStanceDetector,
    TranslatedNLIStanceDetector,
)
from ayorai_attractor.verification.translation import MarianTranslationBackend

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "evals/golden/v0.jsonl"
CORPUS = ROOT / "evals/corpus/documents.jsonl"
OUT_JSON = ROOT / "reports/f1-results.json"
CONFIG = ROOT / "configs/f1-thresholds.json"
OUT_MD = ROOT / "reports/F1-RESULTS.md"
B_TRANSLATOR_MODEL = "Helsinki-NLP/opus-mt-ROMANCE-en"
B_TRANSLATOR_REVISION = "ddfee805aaa57f4bd198f88e8832ba2b012f9ae2"
B_NLI_MODEL = "cross-encoder/nli-deberta-v3-base"
B_NLI_REVISION = "dcaec5ddc7a9456405d53c33bb2d4050ca4f75cf"


def _load_config() -> dict[str, Any]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    window = config["evidence_windows"]
    required = {
        "max_characters",
        "overlap_characters",
        "aggregation",
        "tie_precedence",
    }
    if set(window) != required:
        raise ValueError("f1-thresholds.json evidence_windows schema mismatch")
    if window["aggregation"] != "maximum_confidence_per_stance":
        raise ValueError("unsupported evidence aggregation")
    return config


def _ece(confidences: list[float], correct: list[bool], bins: int = 10) -> float:
    if not confidences:
        return 0.0
    total = len(confidences)
    value = 0.0
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        members = [
            i
            for i, score in enumerate(confidences)
            if low <= score < high
            or (index == bins - 1 and score == high)
        ]
        if not members:
            continue
        accuracy = sum(correct[i] for i in members) / len(members)
        confidence = sum(confidences[i] for i in members) / len(members)
        value += len(members) / total * abs(accuracy - confidence)
    return round(value, 6)


def _evaluate(
    detector: object,
    cases: list[dict[str, Any]],
    corpus: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    scope = RuleScopeClassifier(
        ("medical diagnosis", "diagnóstico", "legal strategy", "estratégia jurídica")
    )
    pipeline = ClaimVerificationPipeline(detector, scope_classifier=scope)
    expected: list[str] = []
    predicted: list[str] = []
    confidences: list[float] = []
    correct: list[bool] = []
    legacy: list[str] = []
    latencies: list[float] = []
    by_category: dict[str, list[bool]] = {}
    by_state: dict[str, list[bool]] = {}
    results: list[dict[str, Any]] = []
    for case in cases:
        if "global" not in case:
            continue
        claims = [str(item["text"]) for item in case.get("expected_claims", [])]
        docs = FixtureRetriever(
            corpus,
            [str(x) for x in case.get("evidence_pool", [])],
        ).retrieve(str(case["query"]))
        started = time.perf_counter()
        result = pipeline.verify(
            claims or [str(case["query"])],
            docs,
        )
        latency = (time.perf_counter() - started) * 1000
        guess = result.verdict.value.upper() if result.verdict else "UNVERIFIED"
        gold = str(case["global"]).upper()
        ok = gold == guess
        expected.append(gold)
        predicted.append(guess)
        confidences.append(float(result.confidence))
        correct.append(ok)
        legacy.append(_legacy_prediction(case, corpus))
        latencies.append(latency)
        by_category.setdefault(str(case["category"]), []).append(ok)
        by_state.setdefault(gold, []).append(ok)
        results.append(
            {
                "id": str(case["id"]),
                "category": str(case["category"]),
                "expected": gold,
                "predicted": guess,
                "confidence": round(float(result.confidence), 6),
                "correct": ok,
                "latency_ms": round(latency, 3),
            }
        )
    majority = Counter(expected).most_common(1)[0]
    boot = bootstrap_accuracy(expected, predicted, iterations=10000, seed=20261003)
    return {
        "system": detector.__class__.__name__,
        "case_count": len(expected),
        "accuracy": round(sum(correct) / len(correct), 6),
        "balanced_accuracy": round(balanced_accuracy(expected, predicted), 6),
        "bootstrap_95_ci": {
            "lower": boot[0],
            "upper": boot[1],
            "iterations": 10000,
            "seed": 20261003,
        },
        "majority_class_baseline": {
            "label": majority[0],
            "accuracy": round(majority[1] / len(expected), 6),
        },
        "confusion_matrix": confusion_matrix(expected, predicted),
        "mcnemar_vs_legacy": {
            "legacy_correct_new_wrong": sum(
                g == old and g != new
                for g, old, new in zip(expected, legacy, predicted, strict=True)
            ),
            "new_correct_legacy_wrong": sum(
                g != old and g == new
                for g, old, new in zip(expected, legacy, predicted, strict=True)
            ),
            "exact_p": mcnemar_exact_pvalue(expected, legacy, predicted),
        },
        "accuracy_by_category": {
            key: {
                "correct": sum(values),
                "total": len(values),
                "accuracy": round(sum(values) / len(values), 6),
            }
            for key, values in sorted(by_category.items())
        },
        "accuracy_by_state": {
            key: {
                "correct": sum(values),
                "total": len(values),
                "accuracy": round(sum(values) / len(values), 6),
            }
            for key, values in sorted(by_state.items())
        },
        "ece": _ece(confidences, correct),
        "latency_ms": {
            "p50": round(statistics.median(latencies), 3),
            "p95": round(
                sorted(latencies)[
                    min(len(latencies) - 1, int(len(latencies) * 0.95))
                ],
                3,
            ),
        },
        "results": results,
        "_predictions": predicted,
    }


def _error_analysis(report: dict[str, Any]) -> dict[str, Any]:
    mapping: dict[str, tuple[str, str]] = {
        "conflict": ("a", "stance/NLI; conflict semantics"),
        "conflict-date": ("a", "stance/NLI; date contradiction"),
        "conflict-entity": ("a", "stance/NLI; entity alignment"),
        "conflict-negation": ("a", "stance/NLI; negation"),
        "numeric-tolerance": ("c", "metadata/numeric"),
        "numeric-tolerance-boundary": ("c", "metadata/numeric"),
        "independence-citation-chain": ("c", "metadata/provenance"),
        "independence-hash": ("c", "metadata/provenance"),
        "independence-republication": ("c", "metadata/independence"),
        "provenance-complete": ("b", "Judge/aggregation"),
        "provenance-incomplete": ("c", "metadata/provenance"),
        "comparison": ("a", "stance/NLI; comparison"),
        "refuted": ("a", "stance/NLI; refutation"),
        "factual": ("a", "stance/NLI"),
        "injection": ("b", "Judge/aggregation"),
        "injection-factual-corroborated": ("b", "Judge/aggregation"),
        "multi-hop": ("b", "Judge/aggregation"),
        "mock-only": ("a", "stance/NLI"),
    }
    counts = Counter()
    cases = []
    for item in report["results"]:
        if item["correct"]:
            continue
        cause, label = mapping.get(
            item["category"],
            ("b", "Judge/aggregation; unclassified"),
        )
        counts[cause] += 1
        cases.append(
            {
                "id": item["id"],
                "category": item["category"],
                "expected": item["expected"],
                "predicted": item["predicted"],
                "cause": label,
                "maximum_resolvable": "1",
            }
        )
    return {
        "case_errors": cases,
        "upper_bound_by_cause": {
            "a": counts["a"],
            "b": counts["b"],
            "c": counts["c"],
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# F1 Results — Golden v0",
        "",
        f"Evaluation commit: {os.environ.get('GITHUB_SHA', 'unknown')}",
        f"CI: {os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
        f"{os.environ.get('GITHUB_REPOSITORY', 'Ayorinha/ayorai-opensearch')}/actions/"
        f"runs/{os.environ.get('GITHUB_RUN_ID', 'unknown')}",
        f"Golden SHA-256: {report['golden_sha256']}",
        f"Corpus SHA-256: {report['corpus_sha256']}",
        f"Threshold/config SHA-256: {report['thresholds_sha256']}",
        f"Seed: {report['seed']}",
        "Bootstrap: 10,000",
        "",
        "## Paths",
        "",
        "| Path | Status |",
        "|---|---|",
        "| A — multilingual direct NLI | measured, EVAL_ONLY |",
        "| B — translate-then-verify | measured, EVAL_ONLY, non-commercial |",
        "| C — rules-only | measured ablation |",
        "",
        "## Metrics",
        "",
        "| System | Accuracy | Balanced | IC95% | ECE | p50 ms | p95 ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key in ("A", "B", "C"):
        item = report[key]
        lines.append(
            f"| {key} | {item['accuracy']:.4f} | {item['balanced_accuracy']:.4f} | "
            f"[{item['bootstrap_95_ci']['lower']:.4f}, "
            f"{item['bootstrap_95_ci']['upper']:.4f}] | {item['ece']:.4f} | "
            f"{item['latency_ms']['p50']:.3f} | {item['latency_ms']['p95']:.3f} |"
        )
    lines.extend(
        [
            f"| Majority baseline | "
            f"{report['A']['majority_class_baseline']['accuracy']:.4f} | — | — | — | — | — |",
            "",
            "## Confusion matrices",
            "",
        ]
    )
    for key in ("A", "B"):
        lines.extend(
            [
                f"### {key}",
                "",
                "| Expected \\ Predicted | "
                + " | ".join(report[key]["confusion_matrix"]["labels"])
                + " |",
                "|---|" + "|".join(["---"] * len(report[key]["confusion_matrix"]["labels"])) + "|",
            ]
        )
        labels = report[key]["confusion_matrix"]["labels"]
        matrix = report[key]["confusion_matrix"]["matrix"]
        for label, row in zip(labels, matrix, strict=True):
            lines.append(f"| {label} | " + " | ".join(str(value) for value in row) + " |")
        lines.append("")
    lines.extend(
        [
            "## McNemar",
            "",
            f"A vs F0/C: {report['mcnemar_A_vs_F0_C']}",
            f"B vs F0/C: {report['mcnemar_B_vs_F0_C']}",
            f"A vs legacy: {report['A']['mcnemar_vs_legacy']}",
            "",
            "## A error analysis",
            "",
            "| Case | Category | Expected | Predicted | Cause | Max resolvable |",
            "|---|---|---|---|---|---:|",
        ]
    )
    for item in report["A_error_analysis"]["case_errors"]:
        lines.append(
            f"| {item['id']} | {item['category']} | {item['expected']} | "
            f"{item['predicted']} | {item['cause']} | {item['maximum_resolvable']} |"
        )
    lines.extend(
        [
            "",
            f"Upper-bound errors by cause: {report['A_error_analysis']['upper_bound_by_cause']}",
            "",
            "## B error analysis",
            "",
            "| Case | Category | Expected | Predicted | Cause | Max resolvable |",
            "|---|---|---|---|---|---:|",
        ]
    )
    for item in report["B_error_analysis"]["case_errors"]:
        lines.append(
            f"| {item['id']} | {item['category']} | {item['expected']} | "
            f"{item['predicted']} | {item['cause']} | {item['maximum_resolvable']} |"
        )
    lines.extend(
        [
            "",
            f"Upper-bound errors by cause: {report['B_error_analysis']['upper_bound_by_cause']}",
            "",
            "## Statistical limitation",
            "",
            "With n=30, exceeding the 43.33% majority baseline with p<0.05 "
            "requires approximately 60% accuracy in this small paired setting. "
            "A's 95% bootstrap interval includes the baseline.",
            "",
            "No threshold was tuned against Golden v0. ADR-002 remains the sole "
            "final-verdict authority.",
            "",
            f"Report SHA-256: {report['report_sha256']}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    config = _load_config()
    window = config["evidence_windows"]
    cases = _load_jsonl(GOLDEN)
    corpus = {str(row["doc_id"]): row for row in _load_jsonl(CORPUS)}

    rule_report = _evaluate(RuleStanceDetector(), cases, corpus)

    a_backend = TransformersNLIBackend(
        EVAL_ONLY_MODEL,
        EVAL_ONLY_REVISION,
        license_level=EVAL_ONLY_LEVEL,
        evaluation_mode=True,
    )
    a_detector = NLIStanceDetector(
        a_backend,
        model=EVAL_ONLY_MODEL,
        version=a_backend.provenance_version,
        window_size=int(window["max_characters"]),
        window_overlap=int(window["overlap_characters"]),
        tie_precedence=str(window["tie_precedence"]),
    )
    a_report = _evaluate(a_detector, cases, corpus)

    b_backend = TransformersNLIBackend(
        B_NLI_MODEL,
        B_NLI_REVISION,
        license_level="EVAL_ONLY",
        evaluation_mode=True,
    )
    b_translator = MarianTranslationBackend(
        B_TRANSLATOR_MODEL,
        B_TRANSLATOR_REVISION,
    )
    b_detector = TranslatedNLIStanceDetector(
        b_backend,
        b_translator,
        model=f"{B_TRANSLATOR_MODEL}+{B_NLI_MODEL}",
        version=f"{b_translator.provenance_version}+{b_backend.provenance_version}",
        window_size=int(window["max_characters"]),
        window_overlap=int(window["overlap_characters"]),
        tie_precedence=str(window["tie_precedence"]),
    )
    b_report = _evaluate(b_detector, cases, corpus)

    gold = [str(case["global"]).upper() for case in cases if "global" in case]
    f0_predictions = rule_report["_predictions"]
    a_predictions = a_report["_predictions"]
    b_predictions = b_report["_predictions"]

    def paired(left: list[str], right: list[str]) -> dict[str, float | int]:
        return {
            "left_correct_right_wrong": sum(
                g == old and g != new
                for g, old, new in zip(gold, left, right, strict=True)
            ),
            "right_correct_left_wrong": sum(
                g != old and g == new
                for g, old, new in zip(gold, left, right, strict=True)
            ),
            "exact_p": mcnemar_exact_pvalue(gold, left, right),
        }

    a_vs_f0 = paired(f0_predictions, a_predictions)
    b_vs_f0 = paired(f0_predictions, b_predictions)
    for report_item in (rule_report, a_report, b_report):
        report_item.pop("_predictions", None)

    report = {
        "suite": "golden-v0",
        "seed": 20261003,
        "golden_cases": len(gold),
        "golden_sha256": hashlib.sha256(GOLDEN.read_bytes()).hexdigest(),
        "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
        "thresholds_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "config": config,
        "A": a_report,
        "B": b_report,
        "C": rule_report,
        "mcnemar_A_vs_F0_C": a_vs_f0,
        "mcnemar_B_vs_F0_C": b_vs_f0,
        "A_error_analysis": {},
        "limitations": [
            "Golden v0 contains 30 scored cases; four ABSTAIN contracts are "
            "outside global-verdict accuracy.",
            "A and B are EVAL_ONLY and are not commercial defaults.",
            "B uses Helsinki-NLP/opus-mt-ROMANCE-en and "
            "cross-encoder/nli-deberta-v3-base.",
            "The original source excerpt remains the audit evidence; "
            "translation is model input only.",
            "With n=30, approximately 60% accuracy is needed to exceed the "
            "43.33% majority baseline with p<0.05; A's IC95% includes the baseline.",
        ],
    }
    report["A_error_analysis"] = _error_analysis(a_report)
    report["B_error_analysis"] = _error_analysis(b_report)
    stable = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    report["report_sha256"] = hashlib.sha256(stable).hexdigest()

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUT_MD.write_text(_markdown(report), encoding="utf-8")
    print(OUT_MD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
