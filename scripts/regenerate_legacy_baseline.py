#!/usr/bin/env python3
"""Regenerate and verify frozen legacy predictions without overwriting the fixture."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ayorai_attractor.evaluation.golden import FixtureSearchProvider, _load_jsonl  # noqa: E402
from ayorai_attractor.models import SearchRequest  # noqa: E402
from ayorai_attractor.orchestrator import Attractor  # noqa: E402

BASELINE = ROOT / "evals/golden/legacy-baseline-v0.jsonl"
MANIFEST = ROOT / "evals/golden/MANIFEST.json"
SUITES = {
    "golden-v0": ROOT / "evals/golden/v0.jsonl",
    "golden-v0.1": ROOT / "evals/golden/v0.1.jsonl",
}


def predict(case: dict[str, Any], documents: dict[str, dict[str, Any]]) -> str:
    provider = FixtureSearchProvider(
        documents, [str(item) for item in case.get("evidence_pool", [])]
    )
    response = Attractor(search_provider=provider).run(
        SearchRequest(query=str(case["query"]), max_agents=5)
    )
    return response.verification.value.upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Compare only; never overwrite.")
    parser.parse_args()
    corpus = _load_jsonl(ROOT / "evals/corpus/documents.jsonl")
    documents = {str(item["doc_id"]): item for item in corpus}
    generated: dict[tuple[str, str], str] = {}
    for suite, path in SUITES.items():
        for case in _load_jsonl(path):
            key = (suite, str(case["id"]))
            if key in generated:
                raise SystemExit(f"duplicate generated key: {key}")
            generated[key] = predict(case, documents)
    frozen: dict[tuple[str, str], str] = {}
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            key = (str(record["suite"]), str(record["case_id"]))
            if key in frozen:
                raise SystemExit(f"duplicate frozen key: {key}")
            frozen[key] = str(record["prediction"])
    if set(generated) != set(frozen):
        raise SystemExit(
            f"key mismatch; missing={sorted(set(generated) - set(frozen))}; "
            f"extra={sorted(set(frozen) - set(generated))}"
        )
    divergences = [
        (key, frozen[key], generated[key])
        for key in sorted(generated)
        if frozen[key] != generated[key]
    ]
    raw = BASELINE.read_bytes()
    expected_hash = json.loads(MANIFEST.read_text(encoding="utf-8"))["legacy_baseline"]["files"][
        "evals/golden/legacy-baseline-v0.jsonl"
    ]["sha256"]
    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != expected_hash:
        raise SystemExit(f"baseline hash mismatch: expected {expected_hash}, got {actual_hash}")
    print(f"records={len(generated)}; unique_keys={len(set(generated))}; sha256={actual_hash}")
    if divergences:
        for key, expected, actual in divergences:
            print(f"DIVERGENCE {key}: frozen={expected} regenerated={actual}")
        return 1
    print("predictions matched: 68/68; divergences: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
