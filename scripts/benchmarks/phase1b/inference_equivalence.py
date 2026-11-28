#!/usr/bin/env python3
"""Score equivalence of the Phase 1b inference stack across dependency versions (P4-01).

Runs ``run_shard.run_inference`` (the exact shard code: protocols, chunking, batching,
pinned model revisions) for mDeBERTa, MiniCheck and FactCG on deterministic synthetic
document/claim pairs and writes every score. Run it under two environments (for example
the historical transformers 4.55.4 lock and a candidate lock) and compare the two
reports with ``--compare``.

No benchmark data is used (no DEV, no TEST): documents are built from the fixed corpus of
``nltk_equivalence`` (hand-written edge cases and seeded synthetic text), and claims are
sentences of the document, perturbed sentences, or sentences of another document.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmarks.phase1b import nltk_equivalence  # noqa: E402

SEED = 20261128
DOCUMENTS = 30
MODELS = ("mdeberta", "minicheck", "factcg")
# Float32 noise bound for "same scores"; decisions at 0.5 must not change at all.
MAX_ABS_DIFF = 1e-5


def records() -> list[tuple[str, dict[str, Any]]]:
    rng = random.Random(SEED)
    pool = [text for _, text in nltk_equivalence.corpus("fixed") if len(text.split()) >= 4]
    rows: list[tuple[str, dict[str, Any]]] = []
    for index in range(DOCUMENTS):
        # Short, medium and long documents, so that every chunking path is exercised.
        size = (1, 5, 20)[index % 3]
        sentences = [rng.choice(pool) for _ in range(size)]
        doc = " ".join(sentences)
        other = rng.choice(pool)
        words = rng.choice(sentences).split()
        rng.shuffle(words)
        claims = {
            "in-doc": rng.choice(sentences),
            "perturbed": " ".join(words),
            "unrelated": other,
        }
        for kind, claim in claims.items():
            rid = hashlib.sha256(f"{index}:{kind}".encode()).hexdigest()
            rows.append((rid, {"doc": doc, "claim": claim, "dataset": f"synthetic-{kind}"}))
    return rows


def run(models: tuple[str, ...] = MODELS) -> dict[str, Any]:
    import torch
    import transformers

    from scripts.benchmarks.phase1b.run_shard import run_inference

    selected = records()
    report: dict[str, Any] = {
        "versions": {"torch": torch.__version__, "transformers": transformers.__version__},
        "records": len(selected),
        "records_sha256": hashlib.sha256(
            json.dumps(selected, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "models": {},
    }
    for model_id in models:
        scored, operational = run_inference(selected, model_id=model_id)
        report["models"][model_id] = {
            "scores": {row["record_id"]: row["score"] for row in scored},
            "block_count": operational["block_count"],
            "token_count_by_unit": operational["token_count_by_unit"],
            "truncation_count": operational["truncation_count"],
        }
    return report


def merge(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Join per-model reports of one environment (run in parallel CI jobs)."""
    merged = {key: value for key, value in reports[0].items() if key != "models"}
    merged["models"] = {}
    for report in reports:
        if report["records_sha256"] != merged["records_sha256"]:
            raise SystemExit("per-model reports were run on different records")
        if report["versions"] != merged["versions"]:
            raise SystemExit("per-model reports come from different environments")
        merged["models"].update(report["models"])
    return merged


def compare(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    if first["records_sha256"] != second["records_sha256"]:
        raise SystemExit("the two reports were run on different records")
    result: dict[str, Any] = {"versions": [first["versions"], second["versions"]], "models": {}}
    for model_id in MODELS:
        a, b = first["models"][model_id], second["models"][model_id]
        diffs = [abs(a["scores"][rid] - b["scores"][rid]) for rid in a["scores"]]
        flips = sum(
            1 for rid in a["scores"] if (a["scores"][rid] >= 0.5) != (b["scores"][rid] >= 0.5)
        )
        same_chunks = (
            a["block_count"] == b["block_count"]
            and a["token_count_by_unit"] == b["token_count_by_unit"]
            and a["truncation_count"] == b["truncation_count"]
        )
        result["models"][model_id] = {
            "max_abs_diff": max(diffs),
            "decision_flips_at_0_5": flips,
            "same_chunking": same_chunks,
            "records_over_bound": sum(1 for d in diffs if d > MAX_ABS_DIFF),
            "chunking": {
                key: [a[key], b[key]]
                for key in ("block_count", "token_count_by_unit", "truncation_count")
                if a[key] != b[key]
            },
            "equivalent": max(diffs) <= MAX_ABS_DIFF and flips == 0 and same_chunks,
        }
    result["equivalent"] = all(m["equivalent"] for m in result["models"].values())
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("BASELINE", "CANDIDATE"))
    parser.add_argument("--model", choices=MODELS, action="append")
    parser.add_argument("--merge", nargs="+", type=Path, metavar="REPORT")
    args = parser.parse_args()
    if args.merge:
        if not args.output:
            parser.error("--output is required with --merge")
        reports = [json.loads(p.read_text(encoding="utf-8")) for p in args.merge]
        args.output.write_text(json.dumps(merge(reports)) + "\n", encoding="utf-8")
        return
    if args.compare:
        first, second = (json.loads(p.read_text(encoding="utf-8")) for p in args.compare)
        result = compare(first, second)
        print(json.dumps(result, indent=2))
        if args.output:
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(0 if result["equivalent"] else 1)
    if not args.output:
        parser.error("--output is required unless --compare is given")
    report = run(tuple(args.model) if args.model else MODELS)
    args.output.write_text(json.dumps(report) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "models"}, indent=2))


if __name__ == "__main__":
    main()
