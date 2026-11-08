#!/usr/bin/env python3
"""Rebuild the record → document association for the DEV score cache (cache v2).

Bootstrapping whole documents needs to know which claims share a document. The v1
cache keeps only ``record_id`` (``sha256`` of the canonical JSON of the full dataset
row), ``cohort``, ``gold`` and ``score``. Because ``record_id`` is a content address,
re-reading the *pinned public DEV file* with the same loader and recomputing
``record_id`` recovers each record's row without the expired inference shards:

- ``doc_id = sha256(canonical_json({"cohort": ..., "doc": ...}))`` — the document text
  exactly as stored (no normalisation), scoped by cohort so the same text in two
  cohorts is never treated as one cluster;
- every cached ``record_id`` must be found (a SHA-256 match on the whole row is a
  cryptographic check that the loader and serialisation are identical);
- the cohort and gold label of every match must agree with the cache;
- the map is built twice and must be identical (determinism);
- the v2 cache must hold exactly the v1 records plus ``doc_id``.

Privacy: only the DEV file is read; the TEST split is never loaded. Dataset text is
used in memory only. The map lives only inside the encrypted v2 cache; the public
summary holds per-cohort aggregate counts.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from collections import defaultdict
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
    from .encrypt_artifact import decode_key
    from .score_cache import (
        RECORD_FIELDS,
        SCHEMA_VERSION,
        SCHEMA_VERSION_V2,
        decrypt_score_cache,
        encrypt_score_cache,
        replay_calibration_v2,
    )
except ImportError:  # direct script execution
    _REPOSITORY_ROOT = str(Path(__file__).resolve().parents[3])
    if _REPOSITORY_ROOT not in sys.path:
        sys.path.insert(0, _REPOSITORY_ROOT)
    from scripts.benchmarks.phase1b.common import (
        DEV_PIN_PATH,
        canonical_json,
        load_records,
        sha256_bytes,
        sha256_file,
        stable_record_id,
    )
    from scripts.benchmarks.phase1b.encrypt_artifact import decode_key
    from scripts.benchmarks.phase1b.score_cache import (
        RECORD_FIELDS,
        SCHEMA_VERSION,
        SCHEMA_VERSION_V2,
        decrypt_score_cache,
        encrypt_score_cache,
        replay_calibration_v2,
    )

DOC_ID_METHOD = 'sha256(canonical_json({"cohort": dataset, "doc": doc}))'
EXPECTED_DEV_FILE = "data/dev-00000-of-00001.parquet"
SUMMARY_SCHEMA = "phase1b-dev-cluster-summary-v1"


def document_id(cohort: str, doc: str) -> str:
    return sha256_bytes(canonical_json({"cohort": cohort, "doc": doc}))


def validate_dev_file(dataset_path: Path, pin: dict[str, Any]) -> None:
    """Accept only the pinned DEV parquet; never a TEST file."""

    if pin.get("file") != EXPECTED_DEV_FILE:
        raise ValueError("the pin does not point to the DEV parquet")
    if "test" in dataset_path.name.lower():
        raise ValueError("TEST data is forbidden in Phase 1b")
    if sha256_file(dataset_path) != pin["sha256"]:
        raise ValueError("DEV dataset SHA-256 does not match the immutable pin")


def build_doc_map(
    rows: list[dict[str, Any]], expected: dict[str, tuple[str, str]]
) -> dict[str, str]:
    """Map every cached record_id to its doc_id; fail on any gap or disagreement.

    ``expected`` maps record_id → (cohort, gold) as stored in the cache.
    """

    index: dict[str, tuple[str, str, str]] = {}
    digest_owner: dict[str, tuple[str, str]] = {}
    for row in rows:
        if "split" in row and str(row["split"]).lower() == "test":
            raise ValueError("TEST rows are forbidden in Phase 1b")
        record_id = stable_record_id(row)
        if record_id in index:
            raise ValueError("duplicate content-addressed DEV row")
        cohort = str(row["dataset"])
        doc = row["doc"]
        if not isinstance(doc, str) or not doc.strip():
            raise ValueError("DEV row has an empty or non-text document")
        label = str(row["label"])
        if label not in {"0", "1"}:
            raise ValueError("DEV label is outside the frozen binary mapping")
        gold = "SUPPORTED" if label == "1" else "NOT_SUPPORTED"
        doc_id = document_id(cohort, doc)
        owner = digest_owner.setdefault(doc_id, (cohort, doc))
        if owner != (cohort, doc):
            raise ValueError("doc_id collision between two distinct documents")
        index[record_id] = (cohort, gold, doc_id)

    missing = [record_id for record_id in expected if record_id not in index]
    if missing:
        raise ValueError(f"{len(missing)} cached records were not found in the DEV file")
    extra = len(index) - len(expected)
    if extra:
        raise ValueError(f"the DEV file has {extra} records that are not in the cache")
    mapping: dict[str, str] = {}
    for record_id, (cohort, gold) in expected.items():
        found_cohort, found_gold, doc_id = index[record_id]
        if (found_cohort, found_gold) != (cohort, gold):
            raise ValueError("cohort or gold label disagrees between the cache and DEV file")
        mapping[record_id] = doc_id
    return dict(sorted(mapping.items()))


def _expected_from_cache(cache: dict[str, Any]) -> dict[str, tuple[str, str]]:
    expected: dict[str, tuple[str, str]] = {}
    for model, entry in sorted(cache["models"].items()):
        for record in entry["records"]:
            key = (record["cohort"], record["gold"])
            previous = expected.setdefault(record["record_id"], key)
            if previous != key:
                raise ValueError(f"{model} disagrees with another member on a record's labels")
    return expected


def build_cache_v2(
    cache: dict[str, Any], mapping: dict[str, str], *, pin: dict[str, Any]
) -> dict[str, Any]:
    if cache.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("cache v2 is built only from a v1 cache")
    models: dict[str, Any] = {}
    for model, entry in sorted(cache["models"].items()):
        records = [dict(record, doc_id=mapping[record["record_id"]]) for record in entry["records"]]
        models[model] = {"protocol": entry.get("protocol"), "records": records}
    v2 = {key: value for key, value in cache.items() if key != "models"}
    v2.update(
        schema_version=SCHEMA_VERSION_V2,
        record_fields=[*RECORD_FIELDS, "doc_id"],
        models=models,
        doc_map={
            "method": DOC_ID_METHOD,
            "dataset_revision": pin["revision"],
            "dataset_sha256": pin["sha256"],
            "doc_map_sha256": sha256_bytes(canonical_json(mapping)),
            "parent_schema_version": SCHEMA_VERSION,
        },
    )
    verify_v2_matches_v1(cache, v2)
    return v2


def verify_v2_matches_v1(v1: dict[str, Any], v2: dict[str, Any]) -> None:
    """v2 must hold exactly the v1 records (ids, cohorts, golds, scores) plus doc_id."""

    if set(v1["models"]) != set(v2["models"]) or v1["record_count"] != v2["record_count"]:
        raise ValueError("cache v2 does not cover the same models and record count")
    for model, entry in v1["models"].items():
        stripped = [
            {field: record[field] for field in RECORD_FIELDS}
            for record in v2["models"][model]["records"]
        ]
        if stripped != entry["records"]:
            raise ValueError(f"cache v2 records for {model} differ from v1")
    if v1.get("calibration_v2_sha256") != v2.get("calibration_v2_sha256"):
        raise ValueError("cache v2 must keep the source calibration digest")


def cluster_summary(cache_v2: dict[str, Any], *, replay_status: str) -> dict[str, Any]:
    """Per-cohort aggregate counts; no identifiers, no per-record values."""

    first_model = sorted(cache_v2["models"])[0]
    per_cohort: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in cache_v2["models"][first_model]["records"]:
        per_cohort[record["cohort"]][record["doc_id"]] += 1
    cohorts: dict[str, Any] = {}
    for cohort in sorted(per_cohort):
        sizes = sorted(per_cohort[cohort].values())
        p90_index = max(0, math.ceil(0.9 * len(sizes)) - 1)  # nearest-rank
        cohorts[cohort] = {
            "claims": sum(sizes),
            "documents": len(sizes),
            "claims_per_document": {
                "min": sizes[0],
                "median": statistics.median(sizes),
                "p90": sizes[p90_index],
                "max": sizes[-1],
                "mean": round(sum(sizes) / len(sizes), 4),
            },
            "share_single_claim_documents": round(
                sum(1 for size in sizes if size == 1) / len(sizes), 4
            ),
        }
    summary = {
        "schema_version": SUMMARY_SCHEMA,
        "split": "dev",
        "source_run_id": cache_v2["source_run_id"],
        "manifest_sha256": cache_v2["manifest_sha256"],
        "doc_id_method": DOC_ID_METHOD,
        "dataset_revision": cache_v2["doc_map"]["dataset_revision"],
        "record_count": cache_v2["record_count"],
        "documents_total": sum(item["documents"] for item in cohorts.values()),
        "cohorts": cohorts,
        "calibration_v2_replay": replay_status,
        "instance_level_output_published": False,
    }
    summary["summary_sha256"] = sha256_bytes(canonical_json(summary))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", required=True, type=Path, help="encrypted v1 cache")
    parser.add_argument("--dataset-path", required=True, type=Path, help="pinned DEV parquet")
    parser.add_argument("--pin", type=Path, default=DEV_PIN_PATH)
    parser.add_argument("--output-cache", required=True, type=Path)
    parser.add_argument("--summary-output", required=True, type=Path)
    parser.add_argument("--code-sha", default=os.environ.get("GITHUB_SHA", "local-uncommitted"))
    parser.add_argument(
        "--skip-replay",
        action="store_true",
        help="tests only: skip the Calibration V2 replay check",
    )
    args = parser.parse_args()

    pin = json.loads(args.pin.read_text(encoding="utf-8"))
    validate_dev_file(args.dataset_path, pin)
    key = decode_key()
    cache = decrypt_score_cache(json.loads(args.cache.read_text(encoding="utf-8")), key=key)
    expected = _expected_from_cache(cache)

    first = build_doc_map(load_records(args.dataset_path), expected)
    second = build_doc_map(load_records(args.dataset_path), expected)
    if canonical_json(first) != canonical_json(second):
        raise SystemExit("doc map is not deterministic")
    cache_v2 = build_cache_v2(cache, first, pin=pin)

    replay_status = "skipped"
    if not args.skip_replay:
        replay = replay_calibration_v2(cache_v2)
        if replay["replay_matches_source"] is not True:
            raise SystemExit(3)
        replay_status = "matches_source"

    envelope = encrypt_score_cache(
        cache_v2, key=key, dataset_revision=pin["revision"], code_sha=args.code_sha
    )
    args.output_cache.parent.mkdir(parents=True, exist_ok=True)
    args.output_cache.write_text(json.dumps(envelope), encoding="utf-8")

    summary = cluster_summary(cache_v2, replay_status=replay_status)
    serialized = canonical_json(summary).decode("utf-8")
    if any(record_id in serialized for record_id in expected):
        raise SystemExit("summary would leak record identifiers")
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_bytes(canonical_json(summary) + b"\n")
    print(
        json.dumps(
            {
                "status": "cache_v2_built",
                "split": "dev",
                "record_count": cache_v2["record_count"],
                "documents_total": summary["documents_total"],
                "doc_map_sha256": cache_v2["doc_map"]["doc_map_sha256"],
                "calibration_v2_replay": replay_status,
                "instance_level_output_published": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
