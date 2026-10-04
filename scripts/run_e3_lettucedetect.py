from __future__ import annotations

import hashlib
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ayorai_attractor.evaluation.golden import _load_jsonl
from ayorai_attractor.evaluation.stats import mcnemar_exact_pvalue
from ayorai_attractor.verification.translation import MarianTranslationBackend

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "evals/corpus/documents.jsonl"
SUITES = {
    "golden-v0": ROOT / "evals/golden/v0.jsonl",
    "golden-v0.1": ROOT / "evals/golden/v0.1.jsonl",
}
F1_REPORT = ROOT / "reports/f1-results.json"
OUT_JSON = ROOT / "reports/e3-lettucedetect-results.json"
OUT_MD = ROOT / "reports/E3-LETTUCEDETECT-RESULTS.md"
TRANSLATOR_MODEL = "Helsinki-NLP/opus-mt-ROMANCE-en"
TRANSLATOR_REVISION = "ddfee805aaa57f4bd198f88e8832ba2b012f9ae2"
SEED = 20261003
BOOTSTRAP = 10000


def binary(label: str) -> str:
    return (        "SUSTENTADO"        if label.upper() in {"SUPPORTS", "SUPPORTED", "VERIFIED"}        else "NAO_SUSTENTADO"    )


def bootstrap_balanced_accuracy(gold: list[str], pred: list[str]) -> tuple[float, float]:
    import random

    rng = random.Random(SEED)
    values: list[float] = []
    n = len(gold)
    for _ in range(BOOTSTRAP):
        idx = [rng.randrange(n) for _ in range(n)]
        sampled_g = [gold[i] for i in idx]
        sampled_p = [pred[i] for i in idx]
        recalls = []
        for label in ("SUSTENTADO", "NAO_SUSTENTADO"):
            total = sum(x == label for x in sampled_g)
            if total:
                recalls.append(                    sum(                        x == label and y == label                        for x, y in zip(sampled_g, sampled_p, strict=True)                    )                    / total                )
        values.append(sum(recalls) / len(recalls) if recalls else 0.0)
    values.sort()
    return values[int(0.025 * (BOOTSTRAP - 1))], values[int(0.975 * (BOOTSTRAP - 1))]


def balanced_accuracy(gold: list[str], pred: list[str]) -> float:
    recalls = []
    for label in ("SUSTENTADO", "NAO_SUSTENTADO"):
        total = sum(x == label for x in gold)
        recalls.append(            (                sum(                    x == label and y == label                    for x, y in zip(gold, pred, strict=True)                )                / total            )            if total            else 0.0        )
    return sum(recalls) / 2


def evaluate_detector(    detector: Any,    cases: list[dict[str, Any]],    corpus: dict[str, dict[str, Any]],    translator: Any | None,) -> dict[str, Any]:
    eligible = [        c        for c in cases        if "global" in c and c.get("expected_claims") and c.get("evidence_pool")    ]
    results = []
    predictions = []
    gold = []
    latencies = []
    by_category: dict[str, list[bool]] = {}

    for case in eligible:
        docs = [corpus[str(doc_id)]["content"] for doc_id in case["evidence_pool"]]
        claim_texts = [str(item["text"]) for item in case["expected_claims"]]
        answer_texts = (            claim_texts            if translator is None            else [translator.translate(x) for x in claim_texts]        )
        started = time.perf_counter()
        spans = []
        for answer in answer_texts:
            out = detector.predict(
                context=docs,
                question=str(case["query"]),
                answer=answer,
                output_format="spans",
            )
            spans.extend(out or [])
        latency = (time.perf_counter() - started) * 1000
        predicted = "NAO_SUSTENTADO" if spans else "SUSTENTADO"
        expected = binary(str(case["global"]))
        ok = predicted == expected
        predictions.append(predicted)
        gold.append(expected)
        latencies.append(latency)
        by_category.setdefault(str(case["category"]), []).append(ok)
        results.append({
            "id": str(case["id"]),
            "category": str(case["category"]),
            "expected": expected,
            "predicted": predicted,
            "unsupported_span_count": len(spans),
            "unsupported_spans": spans,
            "correct": ok,
            "latency_ms": round(latency, 3),
        })

    ci = bootstrap_balanced_accuracy(gold, predictions)
    return {
        "case_count": len(gold),
        "accuracy": round(sum(x == y for x, y in zip(gold, predictions)) / len(gold), 6),
        "balanced_accuracy": round(balanced_accuracy(gold, predictions), 6),
        "bootstrap_95_ci_balanced_accuracy": {            "lower": ci[0],            "upper": ci[1],            "iterations": BOOTSTRAP,            "seed": SEED,        },
        "latency_ms": {
            "p50": round(statistics.median(latencies), 3),
            "p95": round(                sorted(latencies)[                    min(                        len(latencies) - 1,                        math.ceil(0.95 * len(latencies)) - 1,                    )                ],                3,            ),
        },
        "unsupported_case_count": sum(p == "NAO_SUSTENTADO" for p in predictions),
        "coverage": 1.0,
        "abstention_rate": 0.0,
        "accuracy_by_category": {
            k: {"correct": sum(v), "total": len(v), "accuracy": round(sum(v) / len(v), 6)}
            for k, v in sorted(by_category.items())
        },
        "results": results,
        "_gold": gold,
        "_predictions": predictions,
    }


def paired(gold: list[str], left: list[str], right: list[str]) -> dict[str, Any]:
    return {
        "case_count": len(gold),
        "left_correct_right_wrong": sum(            g == a and g != b            for g, a, b in zip(gold, left, right, strict=True)        ),
        "right_correct_left_wrong": sum(            g != a and g == b            for g, a, b in zip(gold, left, right, strict=True)        ),
        "exact_p": mcnemar_exact_pvalue(gold, left, right),
    }


def run_f1() -> None:
    subprocess.run(
        [sys.executable, "scripts/run_f1_eval.py", "--suite", "golden-v0.1"],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    run_f1()
    import importlib

    hf = importlib.import_module("huggingface_hub")
    lettuce = importlib.import_module("lettucedetect.models.inference")
    detector = lettuce.HallucinationDetector(method="transformer")
    model_id = "KRLabsOrg/lettucedect-base-modernbert-en-v1"
    model_revision = str(hf.HfApi().model_info(model_id).sha)
    translator = MarianTranslationBackend(TRANSLATOR_MODEL, TRANSLATOR_REVISION)

    corpus = {str(row["doc_id"]): row for row in _load_jsonl(CORPUS)}
    f1 = json.loads(F1_REPORT.read_text(encoding="utf-8"))
    report: dict[str, Any] = {
        "evaluation_commit": __import__("os").environ.get("GITHUB_SHA", "local"),
        "lettucedetect": {
            "package": __import__("importlib.metadata").metadata.version("lettucedetect"),
            "model": model_id,
            "revision": model_revision,
            "method": "transformer",
            "threshold": "library default; min_confidence not supplied",
            "license": "MIT",
            "license_status": "EVAL_ONLY",
        },
        "translation": {
            "model": TRANSLATOR_MODEL,
            "revision": TRANSLATOR_REVISION,
            "license_status": "EVAL_ONLY",
        },
        "golden": {},
        "golden_sha256": {},
        "notes": [
            "D1: original PT claim as answer, EN documents as context.",
            (                "D2: same PT claim translated PT->EN with the frozen B Opus-MT path, "                "then used as answer against the same EN documents."            ),
            "MADLAD-400 not used.",
            "Span precision/recall/F1 not applicable because Golden has no gold span labels.",
        ],
    }

    for suite, path in SUITES.items():
        cases = _load_jsonl(path)
        d1 = evaluate_detector(detector, cases, corpus, None)
        d2 = evaluate_detector(detector, cases, corpus, translator)

        f1_suite = f1["golden_v0" if suite == "golden-v0" else "golden_v0_1"]
        eligible_ids = [x["id"] for x in d1["results"]]
        f1_by_path = {}
        for key in ("A", "B", "C"):
            items = {x["id"]: x for x in f1_suite[key]["results"]}
            if set(eligible_ids) != set(items):
                raise RuntimeError(f"F1 IDs do not match E3 eligible IDs for {suite} / {key}")
            f1_by_path[key] = [binary(items[i]["predicted"]) for i in eligible_ids]

        gold = d1["_gold"]
        preds = {"D1": d1["_predictions"], "D2": d2["_predictions"], **f1_by_path}
        report["golden"][suite] = {
            "eligible_case_count": len(gold),
            "D1": {k: v for k, v in d1.items() if not k.startswith("_")},
            "D2": {k: v for k, v in d2.items() if not k.startswith("_")},
            "mcnemar_D1_vs_D2": paired(gold, preds["D1"], preds["D2"]),
            "mcnemar_D1_vs_A": paired(gold, preds["D1"], preds["A"]),
            "mcnemar_D1_vs_B": paired(gold, preds["D1"], preds["B"]),
            "mcnemar_D1_vs_C": paired(gold, preds["D1"], preds["C"]),
            "mcnemar_D2_vs_A": paired(gold, preds["D2"], preds["A"]),
            "mcnemar_D2_vs_B": paired(gold, preds["D2"], preds["B"]),
            "mcnemar_D2_vs_C": paired(gold, preds["D2"], preds["C"]),
        }
        report["golden_sha256"][suite] = hashlib.sha256(path.read_bytes()).hexdigest()

    stable = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    report["report_sha256"] = hashlib.sha256(stable).hexdigest()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# E3 LettuceDetect Results",
        "",
        f"Evaluation commit: {report['evaluation_commit']}",
        f"LettuceDetect: {model_id}@{model_revision}",
        f"Package: {report['lettucedetect']['package']}",
        f"Translation: {TRANSLATOR_MODEL}@{TRANSLATOR_REVISION}",
        "Threshold: library default; no min_confidence override.",
        "License status: EVAL_ONLY.",
        "",
    ]
    for suite, title in (("golden-v0", "Golden v0"), ("golden-v0.1", "Golden v0.1")):
        s = report["golden"][suite]
        lines += [
            f"## {title}",
            "",
            "| Arm | Balanced accuracy | IC95% | Accuracy | p50 ms | p95 ms |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for arm in ("D1", "D2"):
            x = s[arm]
            ci = x["bootstrap_95_ci_balanced_accuracy"]
            lines.append(                f"| {arm} | {x['balanced_accuracy']:.4f} | "                f"[{ci['lower']:.4f}, {ci['upper']:.4f}] | "                f"{x['accuracy']:.4f} | {x['latency_ms']['p50']:.3f} | "                f"{x['latency_ms']['p95']:.3f} |"            )
        lines += [            "",            "| Comparison | Left correct / right wrong | Right correct / left wrong | Exact p |",            "|---|---:|---:|---:|",        ]
        for key in (            "mcnemar_D1_vs_D2",            "mcnemar_D1_vs_A",            "mcnemar_D1_vs_B",            "mcnemar_D1_vs_C",            "mcnemar_D2_vs_A",            "mcnemar_D2_vs_B",            "mcnemar_D2_vs_C",        ):
            x=s[key]
            lines.append(                f"| {key} | {x['left_correct_right_wrong']} | "                f"{x['right_correct_left_wrong']} | {x['exact_p']:.6g} |"            )
        lines.append("")
    lines.append(f"Report SHA-256: {report['report_sha256']}")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
