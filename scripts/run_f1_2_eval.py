"""F1.2 measurement: rule path C before and after PR #111.

Pre-registered in docs/eval/PREREGISTRATION-F1.2.md. Two sub-commands:

    measure  run path C (RuleStanceDetector) on Golden v0 and v0.1 with the
             ayorai_attractor package currently importable, and write a JSON
             report with per-case predictions.
    compare  pair a baseline report with a candidate report (same cases) and
             write the F1.2 JSON + Markdown results with exact McNemar.

Both reports are content-addressed with a semantic SHA-256 that excludes
latency. No threshold, rule or Golden case is read from or written by this
script beyond the frozen inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(1, str(ROOT))

SUITES = {
    "golden_v0": ROOT / "evals/golden/v0.jsonl",
    "golden_v0_1": ROOT / "evals/golden/v0.1.jsonl",
}
CORPUS = ROOT / "evals/corpus/documents.jsonl"
SEED = 20261003
ITERATIONS = 10000


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _semantic_sha256(report: dict[str, Any]) -> str:
    def strip(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: strip(item)
                for key, item in value.items()
                if key not in {"latency_ms", "report_sha256"}
            }
        if isinstance(value, list):
            return [strip(item) for item in value]
        return value

    payload = json.dumps(strip(report), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_commit(package_file: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(Path(package_file).parent), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def measure(out: Path) -> dict[str, Any]:
    import ayorai_attractor
    from ayorai_attractor.evaluation.golden import _load_jsonl
    from ayorai_attractor.verification.stance import RuleStanceDetector
    from scripts.run_f1_eval import _evaluate

    corpus = {str(row["doc_id"]): row for row in _load_jsonl(CORPUS)}
    report: dict[str, Any] = {
        "path": "C",
        "detector": "RuleStanceDetector",
        "detector_version": RuleStanceDetector.version,
        "package_file": ayorai_attractor.__file__,
        "source_commit": _source_commit(ayorai_attractor.__file__),
        "corpus_sha256": _sha256_file(CORPUS),
        "seed": SEED,
        "bootstrap_iterations": ITERATIONS,
    }
    for key, path in SUITES.items():
        result = _evaluate(RuleStanceDetector(), _load_jsonl(path), corpus)
        result.pop("_predictions", None)
        result["golden_sha256"] = _sha256_file(path)
        report[key] = result
    report["report_sha256"] = _semantic_sha256(report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _paired(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    from ayorai_attractor.evaluation.stats import mcnemar_exact_pvalue

    left = {item["id"]: item for item in baseline["results"]}
    right = {item["id"]: item for item in candidate["results"]}
    if list(left) != list(right):
        raise ValueError("baseline and candidate must contain the same cases in the same order")
    ids = list(left)
    gold = [left[i]["expected"] for i in ids]
    if gold != [right[i]["expected"] for i in ids]:
        raise ValueError("baseline and candidate gold labels differ")
    before = [left[i]["predicted"] for i in ids]
    after = [right[i]["predicted"] for i in ids]
    changed = [
        {
            "id": i,
            "category": left[i]["category"],
            "expected": left[i]["expected"],
            "baseline": left[i]["predicted"],
            "candidate": right[i]["predicted"],
        }
        for i in ids
        if left[i]["predicted"] != right[i]["predicted"]
    ]
    return {
        "case_count": len(ids),
        "baseline_correct_candidate_wrong": sum(
            g == b and g != a for g, b, a in zip(gold, before, after, strict=True)
        ),
        "candidate_correct_baseline_wrong": sum(
            g != b and g == a for g, b, a in zip(gold, before, after, strict=True)
        ),
        "exact_p": mcnemar_exact_pvalue(gold, before, after),
        "changed_predictions": changed,
    }


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _row(label: str, left: str, right: str) -> str:
    return f"| {label} | {left} | {right} |"


def _ci(item: dict[str, Any]) -> str:
    ci = item["bootstrap_95_ci"]
    return f"[{_pct(ci['lower'])}, {_pct(ci['upper'])}]"


def _markdown(results: dict[str, Any]) -> str:
    base, cand = results["baseline"], results["candidate"]
    prereg = results["preregistration_commit"]
    lines = [
        "# F1.2 Results — rule path C before/after PR #111",
        "",
        f"Pre-registration: docs/eval/PREREGISTRATION-F1.2.md (commit {prereg})",
        f"Baseline: RuleStanceDetector v{base['detector_version']} at {base['source_commit']}",
        f"Candidate: RuleStanceDetector v{cand['detector_version']} at {cand['source_commit']}",
        f"Corpus SHA-256: {cand['corpus_sha256']}",
        f"Seed: {SEED}; bootstrap iterations: {ITERATIONS}",
        f"Baseline report SHA-256: {base['report_sha256']}",
        f"Candidate report SHA-256: {cand['report_sha256']}",
        f"F1.2 results SHA-256: {results['results_sha256']}",
        "",
    ]
    for key, title in (("golden_v0", "Golden v0"), ("golden_v0_1", "Golden v0.1")):
        b, c, p = base[key], cand[key], results["paired"][key]
        majority = _pct(c["majority_class_baseline"]["accuracy"])
        lines += [
            f"## {title}",
            "",
            f"Golden SHA-256: {c['golden_sha256']}",
            "",
            "| Metric | Baseline (v4) | Candidate (v5) |",
            "|---|---:|---:|",
            _row(
                "Balanced accuracy (primary)",
                _pct(b["balanced_accuracy"]),
                _pct(c["balanced_accuracy"]),
            ),
            _row("Accuracy", _pct(b["accuracy"]), _pct(c["accuracy"])),
            _row("Macro-F1", f"{b['macro_f1']:.4f}", f"{c['macro_f1']:.4f}"),
            _row("Accuracy 95% CI", _ci(b), _ci(c)),
            _row("Majority baseline", majority, majority),
            "",
            f"Paired exact McNemar (n={p['case_count']}): baseline correct/candidate wrong = "
            f"{p['baseline_correct_candidate_wrong']}; candidate correct/baseline wrong = "
            f"{p['candidate_correct_baseline_wrong']}; p = {p['exact_p']:.6f}",
            "",
            "Changed predictions:",
            "",
            "| Case | Category | Expected | Baseline | Candidate |",
            "|---|---|---|---|---|",
        ]
        changed = [
            "| "
            + " | ".join((x["id"], x["category"], x["expected"], x["baseline"], x["candidate"]))
            + " |"
            for x in p["changed_predictions"]
        ]
        lines += changed or ["| — | — | — | — | — |"]
        lines += ["", "Accuracy by category (baseline → candidate):", ""]
        for category, item in c["accuracy_by_category"].items():
            fallback = {"correct": 0, "total": item["total"]}
            before = b["accuracy_by_category"].get(category, fallback)
            lines.append(
                f"- {category}: {before['correct']}/{before['total']}"
                f" → {item['correct']}/{item['total']}"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def compare(
    baseline_path: Path, candidate_path: Path, prereg_commit: str, out_json: Path, out_md: Path
) -> None:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    for report in (baseline, candidate):
        if _semantic_sha256(report) != report["report_sha256"]:
            raise ValueError("report_sha256 mismatch")
    results: dict[str, Any] = {
        "preregistration_commit": prereg_commit,
        "baseline": baseline,
        "candidate": candidate,
        "paired": {key: _paired(baseline[key], candidate[key]) for key in SUITES},
    }
    results["results_sha256"] = _semantic_sha256(results)
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(_markdown(results), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("compare")
    c.add_argument("--baseline", type=Path, required=True)
    c.add_argument("--candidate", type=Path, required=True)
    c.add_argument("--preregistration-commit", required=True)
    c.add_argument("--out-json", type=Path, required=True)
    c.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "measure":
        report = measure(args.out)
        print(
            f"detector_version={report['detector_version']} report_sha256={report['report_sha256']}"
        )
    else:
        compare(
            args.baseline, args.candidate, args.preregistration_commit, args.out_json, args.out_md
        )
        print(f"wrote {args.out_json} and {args.out_md}")


if __name__ == "__main__":
    main()
