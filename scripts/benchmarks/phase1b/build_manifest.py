#!/usr/bin/env python3
"""Build a deterministic, metadata-only manifest from the pinned DEV split."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from .common import (
        DEV_PIN_PATH,
        canonical_json,
        load_records,
        sha256_bytes,
        sha256_file,
        stable_record_id,
    )
except ImportError:  # direct script execution
    from common import (
        DEV_PIN_PATH,
        canonical_json,
        load_records,
        sha256_bytes,
        sha256_file,
        stable_record_id,
    )


def _validate_dev_pin(dataset_path: Path, pin_path: Path) -> dict[str, Any]:
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    actual = sha256_file(dataset_path)
    if actual != pin["sha256"]:
        raise ValueError("DEV dataset SHA-256 does not match the immutable pin")
    return pin


def build_manifest(
    rows: list[dict[str, Any]],
    *,
    dataset_sha256: str,
    dataset_revision: str,
    code_sha: str,
    split: str = "dev",
    shard_size: int = 1000,
    sample_size: int | None = None,
    seed: int = 20261106,
    sample_per_cohort: int | None = None,
    max_shards: int | None = None,
) -> dict[str, Any]:
    if split != "dev":
        raise ValueError("Phase 1b implementation is DEV-only; TEST is forbidden")
    if shard_size < 1 or (sample_size is not None and sample_size < 1):
        raise ValueError("sample and shard sizes must be positive")
    required = {"doc", "claim", "label", "dataset"}
    if not rows or any(not required.issubset(row) for row in rows):
        raise ValueError("DEV rows do not match the pinned LLM-AggreFact schema")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        rid = stable_record_id(row)
        if rid in indexed:
            raise ValueError("duplicate content-addressed DEV row")
        label = str(row["label"])
        if label not in {"0", "1"}:
            raise ValueError("DEV label is outside the frozen binary mapping")
        if not str(row["doc"]).strip() or not str(row["claim"]).strip():
            raise ValueError("DEV row contains an empty document or claim")
        indexed[rid] = row

    selected = sorted(indexed)
    if sample_per_cohort is not None:
        by_cohort: dict[str, list[str]] = {}
        for rid in selected:
            by_cohort.setdefault(str(indexed[rid]["dataset"]), []).append(rid)
        rng = random.Random(seed)
        chosen: list[str] = []
        for cohort in sorted(by_cohort):
            ids = by_cohort[cohort]
            rng.shuffle(ids)
            chosen.extend(ids[:sample_per_cohort])
        selected = sorted(chosen)
    elif sample_size is not None and sample_size < len(selected):
        # Deterministic, cohort-stratified proportional sample with stable tie-breaks.
        groups: dict[str, list[str]] = {}
        for rid in selected:
            groups.setdefault(str(indexed[rid]["dataset"]), []).append(rid)
        exact = {key: sample_size * len(ids) / len(selected) for key, ids in groups.items()}
        counts = {key: int(value) for key, value in exact.items()}
        remaining = sample_size - sum(counts.values())
        for key in sorted(groups, key=lambda k: (-(exact[k] - counts[k]), k))[:remaining]:
            counts[key] += 1
        rng = random.Random(seed)
        chosen = []
        for cohort in sorted(groups):
            ids = groups[cohort][:]
            rng.shuffle(ids)
            chosen.extend(ids[:counts[cohort]])
        selected = sorted(chosen)

    shards = []
    for offset in range(0, len(selected), shard_size):
        shard_ids = selected[offset : offset + shard_size]
        shards.append({
            "shard_id": f"dev-{offset // shard_size:04d}",
            "start": offset,
            "count": len(shard_ids),
            "record_ids": shard_ids,
            "record_ids_sha256": sha256_bytes(canonical_json(shard_ids)),
        })
    if max_shards is not None:
        if max_shards < 1:
            raise ValueError("max_shards must be positive")
        shards = shards[:max_shards]
        selected = [rid for shard in shards for rid in shard["record_ids"]]
    cohort_counts = Counter(str(indexed[rid]["dataset"]) for rid in selected)
    manifest: dict[str, Any] = {
        "schema_version": "phase1b-dev-manifest-v1",
        "split": "dev",
        "dataset": "lytang/LLM-AggreFact",
        "dataset_revision": dataset_revision,
        "dataset_sha256": dataset_sha256,
        "code_sha": code_sha,
        "seed": seed,
        "shard_size": shard_size,
        "sample_count": len(selected),
        "cohort_counts": dict(sorted(cohort_counts.items())),
        "shards": shards,
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical_json(manifest))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-path", required=True, type=Path)
    parser.add_argument("--pin", type=Path, default=DEV_PIN_PATH)
    parser.add_argument("--split", choices=["dev"], default="dev")
    parser.add_argument("--shard-size", type=int, default=1000)
    parser.add_argument("--sample-size", type=int)
    parser.add_argument("--sample-per-cohort", type=int)
    parser.add_argument("--max-shards", type=int)
    parser.add_argument("--seed", type=int, default=20261106)
    parser.add_argument("--code-sha", default=None)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    pin = _validate_dev_pin(args.dataset_path, args.pin)
    import os
    code_sha = args.code_sha or os.environ.get("GITHUB_SHA", "local-uncommitted")
    manifest = build_manifest(
        load_records(args.dataset_path),
        dataset_sha256=pin["sha256"],
        dataset_revision=pin["revision"],
        code_sha=code_sha,
        split=args.split,
        shard_size=args.shard_size,
        sample_size=args.sample_size,
        sample_per_cohort=args.sample_per_cohort,
        seed=args.seed,
        max_shards=args.max_shards,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(manifest) + b"\n")
    print(json.dumps({
        "status": "manifest_created",
        "split": "dev",
        "sample_count": manifest["sample_count"],
        "shard_count": len(manifest["shards"]),
        "manifest_sha256": manifest["manifest_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
