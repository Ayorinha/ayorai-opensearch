from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from run_f1_eval import _evaluate

from ayorai_attractor.evaluation.golden import _load_jsonl
from ayorai_attractor.evaluation.stats import mcnemar_exact_pvalue
from ayorai_attractor.verification.nli import (
    EVAL_ONLY_LEVEL,
    EVAL_ONLY_MODEL,
    EVAL_ONLY_REVISION,
    TransformersNLIBackend,
)
from ayorai_attractor.verification.stance import (
    NLIStanceDetector,
    SentenceNLIStanceDetector,
    SentenceTranslatedNLIStanceDetector,
    TranslatedNLIStanceDetector,
)
from ayorai_attractor.verification.translation import MarianTranslationBackend

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "evals/corpus/documents.jsonl"
OUT_JSON = ROOT / "reports/h1-results.json"
OUT_MD = ROOT / "reports/H1-RESULTS.md"
A_MODEL = EVAL_ONLY_MODEL
A_REVISION = EVAL_ONLY_REVISION
B_TRANSLATOR = "Helsinki-NLP/opus-mt-ROMANCE-en"
B_TRANSLATOR_REVISION = "ddfee805aaa57f4bd198f88e8832ba2b012f9ae2"
B_MODEL = "cross-encoder/nli-deberta-v3-base"
B_REVISION = "dcaec5ddc7a9456405d53c33bb2d4050ca4f75cf"


def _paired(base: dict[str, Any], h1: dict[str, Any]) -> dict[str, Any]:
    left = {x["id"]: x for x in base["results"]}
    right = {x["id"]: x for x in h1["results"]}
    ids = sorted(left)
    gold = [left[i]["expected"] for i in ids]
    base_pred = [left[i]["predicted"] for i in ids]
    h1_pred = [right[i]["predicted"] for i in ids]
    return {
        "case_count": len(ids),
        "baseline_correct_h1_wrong": sum(
            g == b and g != h for g, b, h in zip(gold, base_pred, h1_pred, strict=True)
        ),
        "h1_correct_baseline_wrong": sum(
            g != b and g == h for g, b, h in zip(gold, base_pred, h1_pred, strict=True)
        ),
        "exact_p": mcnemar_exact_pvalue(gold, base_pred, h1_pred),
    }


def _suite(cases: list[dict[str, Any]], corpus: dict[str, dict[str, Any]]) -> dict[str, Any]:
    a_backend = TransformersNLIBackend(
        A_MODEL, A_REVISION, license_level=EVAL_ONLY_LEVEL, evaluation_mode=True
    )
    b_backend = TransformersNLIBackend(
        B_MODEL, B_REVISION, license_level="COMMERCIAL_DEFAULT"
    )
    translator = MarianTranslationBackend(
        B_TRANSLATOR, B_TRANSLATOR_REVISION,
        license_level=EVAL_ONLY_LEVEL, evaluation_mode=True,
    )
    a_base = NLIStanceDetector(
        a_backend, model=A_MODEL, version=a_backend.provenance_version,
        window_size=512, window_overlap=64, tie_precedence="contradicts"
    )
    a_h1 = SentenceNLIStanceDetector(
        a_backend, model=A_MODEL, version=a_backend.provenance_version,
        window_size=512, window_overlap=64, tie_precedence="contradicts"
    )
    b_base = TranslatedNLIStanceDetector(
        b_backend, translator, model=f"{B_TRANSLATOR}+{B_MODEL}",
        version=f"{translator.provenance_version}+{b_backend.provenance_version}",
        window_size=512, window_overlap=64, tie_precedence="contradicts"
    )
    b_h1 = SentenceTranslatedNLIStanceDetector(
        b_backend, translator, model=f"{B_TRANSLATOR}+{B_MODEL}",
        version=f"{translator.provenance_version}+{b_backend.provenance_version}",
        window_size=512, window_overlap=64, tie_precedence="contradicts"
    )
    return {
        "A_baseline": _evaluate(a_base, cases, corpus),
        "A_H1": _evaluate(a_h1, cases, corpus),
        "B_baseline": _evaluate(b_base, cases, corpus),
        "B_H1": _evaluate(b_h1, cases, corpus),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite", choices=("golden-v0", "golden-v0.1"), default="golden-v0.1"
    )
    parser.parse_args()
    corpus = {str(x["doc_id"]): x for x in _load_jsonl(CORPUS)}
    paths = {
        "golden-v0": ROOT / "evals/golden/v0.jsonl",
        "golden-v0.1": ROOT / "evals/golden/v0.1.jsonl",
    }
    results: dict[str, Any] = {}
    for name, path in paths.items():
        results[name] = _suite(_load_jsonl(path), corpus)
        for pair in (("A_baseline", "A_H1"), ("B_baseline", "B_H1")):
            results[name][f"mcnemar_{pair[0]}_vs_{pair[1]}"] = _paired(
                results[name][pair[0]], results[name][pair[1]]
            )
    report = {
        "commit": __import__("os").environ.get("GITHUB_SHA", "unknown"),
        "golden_v0_sha256": hashlib.sha256(paths["golden-v0"].read_bytes()).hexdigest(),
        "golden_v0_1_sha256": hashlib.sha256(paths["golden-v0.1"].read_bytes()).hexdigest(),
        "models": {
            "A": {"model": A_MODEL, "revision": A_REVISION, "license": "EVAL_ONLY"},
            "B_nli": {"model": B_MODEL, "revision": B_REVISION, "license": "EVAL_ONLY"},
            "B_translation": {"model": B_TRANSLATOR, "revision": B_TRANSLATOR_REVISION},
        },
        "seed": 20261003,
        "bootstrap_iterations": 10000,
        "method": (
            "sentence-level evidence, claim x sentence, max confidence, "
            "contradicts tie precedence"
        ),
        "golden_v0": results["golden-v0"],
        "golden_v0_1": results["golden-v0.1"],
    }
    stable = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    report["report_sha256"] = hashlib.sha256(stable).hexdigest()
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# H1 Results — Sentence Aggregation",
        "",
        f"Commit: {report['commit']}",
        "Seed: 20261003",
        "Bootstrap: 10,000",
        "",
    ]
    for suite in ("golden-v0", "golden-v0.1"):
        lines += [
            f"## {suite}",
            "",
            "| Path | Accuracy | Balanced | Macro-F1 | IC95% | ECE | p50 ms | p95 ms |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for key in ("A_baseline", "A_H1", "B_baseline", "B_H1"):
            x = results[suite][key]
            lines.append(
                f"| {key} | {x['accuracy']:.4f} | "
                f"{x['balanced_accuracy']:.4f} | {x['macro_f1']:.4f} | "
                f"[{x['bootstrap_95_ci']['lower']:.4f}, "
                f"{x['bootstrap_95_ci']['upper']:.4f}] | {x['ece']:.4f} | "
                f"{x['latency_ms']['p50']:.3f} | {x['latency_ms']['p95']:.3f} |"
            )
        for key in ("A", "B"):
            x = results[suite][f"mcnemar_{key}_baseline_vs_{key}_H1"]
            lines.append(
                f"McNemar {key}: {x['baseline_correct_h1_wrong']}/"
                f"{x['h1_correct_baseline_wrong']} p={x['exact_p']:.6g}"
            )
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    report["json_sha256"] = hashlib.sha256(OUT_JSON.read_bytes()).hexdigest()
    report["markdown_sha256"] = hashlib.sha256(OUT_MD.read_bytes()).hexdigest()
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n".join(lines))
    

if __name__ == "__main__":
    main()
