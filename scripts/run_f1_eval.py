from __future__ import annotations

import argparse
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


def _paired(left: dict[str, Any], right: dict[str, Any]) -> dict[str, float | int]:
    left_by_id = {item["id"]: item for item in left["results"]}
    right_by_id = {item["id"]: item for item in right["results"]}
    ids = sorted(set(left_by_id) & set(right_by_id))
    if len(ids) != len(left_by_id) or len(ids) != len(right_by_id):
        raise ValueError("v0/v0.1 case ids do not match")
    gold = [left_by_id[item]["expected"] for item in ids]
    predictions_left = [left_by_id[item]["predicted"] for item in ids]
    predictions_right = [right_by_id[item]["predicted"] for item in ids]
    return {
        "case_count": len(ids),
        "left_correct_right_wrong": sum(
            g == x and g != y
            for g, x, y in zip(gold, predictions_left, predictions_right, strict=True)
        ),
        "right_correct_left_wrong": sum(
            g != x and g == y
            for g, x, y in zip(gold, predictions_left, predictions_right, strict=True)
        ),
        "exact_p": mcnemar_exact_pvalue(gold, predictions_left, predictions_right),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# F1 Results — Golden v0 / v0.1",
        "",
        f"Evaluation commit: {os.environ.get('GITHUB_SHA', 'unknown')}",
        f"CI: {os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
        f"{os.environ.get('GITHUB_REPOSITORY', 'Ayorinha/ayorai-opensearch')}/actions/"
        f"runs/{os.environ.get('GITHUB_RUN_ID', 'unknown')}",
        f"Seed: {report['seed']}",
        "Bootstrap: 10,000",
        "",
        "Both frozen development Goldens were evaluated with identical code, thresholds and models.",
        "",
    ]
    for suite_key, title in (("golden_v0", "Golden v0"), ("golden_v0_1", "Golden v0.1")):
        suite = report[suite_key]
        lines += [
            f"## {title}", "",
            f"Golden SHA-256: {suite['golden_sha256']}", "",
            "| Path | Accuracy | Balanced | IC95% | ECE | p50 ms | p95 ms |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for key in ("A", "B", "C"):
            item = suite[key]
            lines.append(
                f"| {key} | {item['accuracy']:.4f} | {item['balanced_accuracy']:.4f} | "
                f"[{item['bootstrap_95_ci']['lower']:.4f}, {item['bootstrap_95_ci']['upper']:.4f}] | "
                f"{item['ece']:.4f} | {item['latency_ms']['p50']:.3f} | {item['latency_ms']['p95']:.3f} |"
            )
        lines.append(
            f"| Majority baseline | {suite['A']['majority_class_baseline']['accuracy']:.4f} | — | — | — | — | — |"
        )
        lines.append("")
    lines += [
        "## Paired McNemar — v0 vs v0.1", "",
        "| Path | v0 correct / v0.1 wrong | v0.1 correct / v0 wrong | Exact p |",
        "|---|---:|---:|---:|",
    ]
    for key in ("A", "B", "C"):
        item = report["mcnemar_v0_vs_v0_1"][key]
        lines.append(
            f"| {key} | {item['left_correct_right_wrong']} | "
            f"{item['right_correct_left_wrong']} | {item['exact_p']:.6g} |"
        )
    lines += ["", f"Internal report content SHA-256: {report['report_sha256']}", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite",
        choices=("golden-v0", "golden-v0.1"),
        default="golden-v0.1",
    )
    args = parser.parse_args()
    config = _load_config()
    window = config["evidence_windows"]
    corpus = {str(row["doc_id"]): row for row in _load_jsonl(CORPUS)}
    suite_paths = {
        "golden-v0": ROOT / "evals/golden/v0.jsonl",
        "golden-v0.1": ROOT / "evals/golden/v0.1.jsonl",
    }

    def evaluate_suite(path: Path) -> dict[str, Any]:
        cases = _load_jsonl(path)
        rule_report = _evaluate(RuleStanceDetector(), cases, corpus)

        a_backend = TransformersNLIBackend(
            EVAL_ONLY_MODEL, EVAL_ONLY_REVISION,
            license_level=EVAL_ONLY_LEVEL, evaluation_mode=True,
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
            B_NLI_MODEL, B_NLI_REVISION,
            license_level="EVAL_ONLY", evaluation_mode=True,
        )
        b_translator = MarianTranslationBackend(
            B_TRANSLATOR_MODEL, B_TRANSLATOR_REVISION,
        )
        b_detector = TranslatedNLIStanceDetector(
            b_backend, b_translator,
            model=f"{B_TRANSLATOR_MODEL}+{B_NLI_MODEL}",
            version=f"{b_translator.provenance_version}+{b_backend.provenance_version}",
            window_size=int(window["max_characters"]),
            window_overlap=int(window["overlap_characters"]),
            tie_precedence=str(window["tie_precedence"]),
        )
        b_report = _evaluate(b_detector, cases, corpus)
        predictions = {
            "A": a_report.pop("_predictions"),
            "B": b_report.pop("_predictions"),
            "C": rule_report.pop("_predictions"),
        }
        return {
            "golden_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "A": a_report,
            "B": b_report,
            "C": rule_report,
            "_predictions": predictions,
        }

    v0 = evaluate_suite(suite_paths["golden-v0"])
    v01 = evaluate_suite(suite_paths["golden-v0.1"])
    paired = {
        key: _paired(
            {**v0[key], "results": v0[key]["results"]},
            {**v01[key], "results": v01[key]["results"]},
        )
        for key in ("A", "B", "C")
    }
    v0.pop("_predictions")
    v01.pop("_predictions")

    report = {
        "suite": args.suite,
        "comparison": "golden-v0 vs golden-v0.1",
        "seed": 20261003,
        "bootstrap_iterations": 10000,
        "thresholds_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "golden_v0": v0,
        "golden_v0_1": v01,
        "mcnemar_v0_vs_v0_1": paired,
    }
    stable = json.dumps(
        report, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    report["report_sha256"] = hashlib.sha256(stable).hexdigest()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUT_MD.write_text(_markdown(report), encoding="utf-8")
    print(_markdown(report))


if __name__ == "__main__":
    main()
