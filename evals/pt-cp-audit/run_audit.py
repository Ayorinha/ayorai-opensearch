"""Evaluate a stance detector on the PT-CP-Audit simulation.

Usage:
    python evals/pt-cp-audit/run_audit.py --split dev  [--show-cases]
    python evals/pt-cp-audit/run_audit.py --split test --out reports/pt-cp-audit-test.json

Per-case output is only printed for the dev split. The test split is reported in
aggregate so it can stay a held-out measurement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.models import Claim, Evidence
from ayorai_attractor.verification.stance import RuleStanceDetector

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases.jsonl"
LABELS = ("supports", "contradicts", "neutral")


def _claim(text: str) -> ExtractedClaim:
    return ExtractedClaim(
        claim=Claim(id="c1", text=text),
        confidence=1.0,
        provenance=ComponentProvenance("audit", "pt-cp-audit", "1", "in", "out"),
    )


def _evidence(case: dict[str, Any]) -> Evidence:
    text = str(case["evidence"])
    return Evidence(
        id="e1",
        claim_id="c1",
        source_id=str(case["evidence_id"]),
        source_location=str(case["source_url"]),
        retrieved_at=datetime(2026, 9, 15, tzinfo=UTC),
        start_offset=0,
        end_offset=len(text),
        excerpt=text,
        canonical_url=str(case["source_url"]),
    )


def evaluate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    detector = RuleStanceDetector()
    rows = []
    for case in cases:
        edge = detector.detect([_claim(case["claim"])], [_evidence(case)]).edges[0].edge
        rows.append({**case, "predicted": edge.stance.value})
    gold = [r["label"] for r in rows]
    pred = [r["predicted"] for r in rows]
    total = len(rows)
    confusion = {g: {p: 0 for p in LABELS} for g in LABELS}
    for g, p in zip(gold, pred, strict=True):
        confusion[g][p] += 1
    per_class = {}
    for label in LABELS:
        tp = confusion[label][label]
        predicted = sum(confusion[g][label] for g in LABELS)
        actual = sum(confusion[label].values())
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": actual,
        }
    not_supported = [r for r in rows if r["label"] != "supports"]
    false_support = sum(r["predicted"] == "supports" for r in not_supported)
    not_contra = [r for r in rows if r["label"] != "contradicts"]
    false_contra = sum(r["predicted"] == "contradicts" for r in not_contra)
    by_type: dict[str, list[bool]] = {}
    for r in rows:
        by_type.setdefault(r["type"], []).append(r["label"] == r["predicted"])
    return {
        "detector": f"RuleStanceDetector v{RuleStanceDetector.version}",
        "cases": total,
        "cases_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest(),
        "accuracy": round(sum(g == p for g, p in zip(gold, pred, strict=True)) / total, 4),
        "macro_f1": round(sum(v["f1"] for v in per_class.values()) / len(LABELS), 4),
        "per_class": per_class,
        "confusion": confusion,
        "false_support_rate": round(false_support / len(not_supported), 4),
        "false_contradiction_rate": round(false_contra / len(not_contra), 4),
        "predicted_distribution": dict(Counter(pred)),
        "accuracy_by_type": {k: f"{sum(v)}/{len(v)}" for k, v in sorted(by_type.items())},
        "_rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "test", "all"), required=True)
    parser.add_argument("--show-cases", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines()]
    if args.split != "all":
        cases = [c for c in cases if c["split"] == args.split]
    report = evaluate(cases)
    rows = report.pop("_rows")
    if args.show_cases and args.split == "dev":
        for r in rows:
            mark = "OK " if r["label"] == r["predicted"] else "ERR"
            print(
                f"{mark} {r['id']} {r['type']:<20} gold={r['label']:<11} "
                f"pred={r['predicted']:<11} {r['claim'][:90]}"
            )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
