#!/usr/bin/env python3
"""Encrypted DEV score and label caches (roadmap v0.8, item A1).

Predictions and gold labels are stored in separate AES-256-GCM envelopes and
use separate 256-bit secrets. They are joined only in the evaluation process.
No plaintext per-instance artifact is written or uploaded.

The score cache contains only record_id, cohort, score and optional doc_id.
The label cache contains only record_id, cohort and gold. Both are DEV-only.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from .common import atomic_write_bytes, canonical_json, sha256_bytes
    from .encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes
except ImportError:  # direct script execution
    _REPOSITORY_ROOT = str(Path(__file__).resolve().parents[3])
    if _REPOSITORY_ROOT not in sys.path:
        sys.path.insert(0, _REPOSITORY_ROOT)
    from common import atomic_write_bytes, canonical_json, sha256_bytes
    from encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes

SCORE_SCHEMA_VERSION = "phase1b-dev-score-cache-v3"
SCORE_SCHEMA_VERSION_V2 = "phase1b-dev-score-cache-v4"
LABEL_SCHEMA_VERSION = "phase1b-dev-gold-label-cache-v1"
SCORE_CACHE_SHARD_ID = "dev-score-cache"
GOLD_LABEL_CACHE_SHARD_ID = "dev-gold-labels"
SCORE_RECORD_FIELDS = ("record_id", "cohort", "score")
SCORE_RECORD_FIELDS_V2 = (*SCORE_RECORD_FIELDS, "doc_id")
LABEL_RECORD_FIELDS = ("record_id", "cohort", "gold")
GOLD_VALUES = frozenset({"SUPPORTED", "NOT_SUPPORTED"})
_HEX64 = re.compile(r"[0-9a-f]{64}")


def _clean_score_record(record: dict[str, Any]) -> dict[str, Any]:
    if "gold" in record:
        raise ValueError("gold labels must never be included in the score cache")
    required = set(SCORE_RECORD_FIELDS)
    if not required.issubset(record):
        raise ValueError(f"score record is missing fields: {sorted(required - set(record))}")
    record_id, cohort, score = record["record_id"], record["cohort"], record["score"]
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("record_id must be a non-empty string")
    if not isinstance(cohort, str) or not cohort:
        raise ValueError("cohort must be a non-empty string")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("score must be numeric")
    if not math.isfinite(float(score)) or not 0.0 <= float(score) <= 1.0:
        raise ValueError("score must be finite and within [0, 1]")
    cleaned = {"record_id": record_id, "cohort": cohort, "score": float(score)}
    if "doc_id" in record:
        doc_id = record["doc_id"]
        if not isinstance(doc_id, str) or not _HEX64.fullmatch(doc_id):
            raise ValueError("doc_id must be a 64-character lowercase hex digest")
        cleaned["doc_id"] = doc_id
    return cleaned


def _clean_label_record(record: dict[str, Any]) -> dict[str, str]:
    if not set(LABEL_RECORD_FIELDS).issubset(record):
        raise ValueError("gold-label record is missing required fields")
    record_id, cohort, gold = record["record_id"], record["cohort"], record["gold"]
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("record_id must be a non-empty string")
    if not isinstance(cohort, str) or not cohort:
        raise ValueError("cohort must be a non-empty string")
    if gold not in GOLD_VALUES:
        raise ValueError("gold must be SUPPORTED or NOT_SUPPORTED")
    return {"record_id": record_id, "cohort": cohort, "gold": gold}


def _unique_sorted(rows: list[dict[str, Any]], cleaner: Any, label: str) -> list[dict[str, Any]]:
    cleaned = [cleaner(record) for record in rows]
    ids = [record["record_id"] for record in cleaned]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate record_id in {label}")
    return sorted(cleaned, key=lambda record: record["record_id"])


def build_score_cache(
    rows_by_model: dict[str, list[dict[str, Any]]],
    *,
    protocols: dict[str, Any],
    manifest_sha256: str,
    source_run_id: str,
    calibration_v2: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build prediction-only cache payload; gold labels are rejected, not copied."""
    if not rows_by_model:
        raise ValueError("score cache requires at least one model")
    models: dict[str, Any] = {}
    reference_ids: set[str] | None = None
    for model in sorted(rows_by_model):
        records = _unique_sorted(
            rows_by_model[model], _clean_score_record, f"score cache for {model}"
        )
        ids = {record["record_id"] for record in records}
        if reference_ids is None:
            reference_ids = ids
        elif ids != reference_ids:
            raise ValueError("all models must cover the same DEV records")
        models[model] = {"protocol": protocols.get(model), "records": records}
    return {
        "schema_version": SCORE_SCHEMA_VERSION,
        "split": "dev",
        "source_run_id": str(source_run_id),
        "manifest_sha256": manifest_sha256,
        "record_count": len(reference_ids or ()),
        "record_fields": list(SCORE_RECORD_FIELDS),
        "calibration_v2_sha256": (
            sha256_bytes(canonical_json(calibration_v2)) if calibration_v2 is not None else None
        ),
        "models": models,
    }


def build_gold_label_cache(
    labels: list[dict[str, Any]],
    *,
    manifest_sha256: str,
    source_run_id: str,
) -> dict[str, Any]:
    """Build the separately encrypted gold-label payload."""
    records = _unique_sorted(labels, _clean_label_record, "gold-label cache")
    return {
        "schema_version": LABEL_SCHEMA_VERSION,
        "split": "dev",
        "source_run_id": str(source_run_id),
        "manifest_sha256": manifest_sha256,
        "record_count": len(records),
        "record_fields": list(LABEL_RECORD_FIELDS),
        "records": records,
    }


def _cache_metadata(
    *, source_run_id: str, shard_id: str, model_revision: str, dataset_revision: str, code_sha: str
) -> dict[str, str]:
    return {
        "run_id": str(source_run_id),
        "split": "dev",
        "model_revision": model_revision,
        "shard_id": shard_id,
        "dataset_revision": dataset_revision,
        "code_sha": code_sha,
    }


def encrypt_score_cache(
    cache: dict[str, Any], *, key: bytes, dataset_revision: str, code_sha: str
) -> dict[str, Any]:
    if (
        cache.get("schema_version") not in {SCORE_SCHEMA_VERSION, SCORE_SCHEMA_VERSION_V2}
        or cache.get("split") != "dev"
    ):
        raise ValueError("only supported DEV score caches may be encrypted")
    metadata = _cache_metadata(
        source_run_id=cache["source_run_id"],
        shard_id=SCORE_CACHE_SHARD_ID,
        model_revision="multi-model-score-cache",
        dataset_revision=dataset_revision,
        code_sha=code_sha,
    )
    return encrypt_bytes(canonical_json(cache), key=key, metadata=metadata)


def decrypt_score_cache(envelope: dict[str, Any], *, key: bytes) -> dict[str, Any]:
    metadata = envelope.get("metadata") or {}
    if (
        metadata.get("shard_id") != SCORE_CACHE_SHARD_ID
        or metadata.get("split") != "dev"
        or metadata.get("model_revision") != "multi-model-score-cache"
    ):
        raise ValueError("envelope is not a DEV score cache")
    cache = json.loads(decrypt_bytes(envelope, key=key))
    schema = cache.get("schema_version")
    if schema not in {SCORE_SCHEMA_VERSION, SCORE_SCHEMA_VERSION_V2} or cache.get("split") != "dev":
        raise ValueError("unsupported score cache payload; legacy caches must be regenerated")
    if str(cache.get("source_run_id")) != str(metadata.get("run_id")):
        raise ValueError("score cache payload does not match its envelope metadata")
    for model, entry in cache["models"].items():
        records = _unique_sorted(entry["records"], _clean_score_record, f"score cache for {model}")
        if schema == SCORE_SCHEMA_VERSION_V2 and any("doc_id" not in record for record in records):
            raise ValueError("cache v4 record is missing doc_id")
        if len(records) != cache["record_count"]:
            raise ValueError(f"score cache for {model} has an unexpected record count")
        entry["records"] = records
    return cache


def encrypt_gold_label_cache(
    cache: dict[str, Any], *, key: bytes, dataset_revision: str, code_sha: str
) -> dict[str, Any]:
    if cache.get("schema_version") != LABEL_SCHEMA_VERSION or cache.get("split") != "dev":
        raise ValueError("only DEV gold-label caches may be encrypted")
    metadata = _cache_metadata(
        source_run_id=cache["source_run_id"],
        shard_id=GOLD_LABEL_CACHE_SHARD_ID,
        model_revision="gold-labels",
        dataset_revision=dataset_revision,
        code_sha=code_sha,
    )
    return encrypt_bytes(canonical_json(cache), key=key, metadata=metadata)


def decrypt_gold_label_cache(envelope: dict[str, Any], *, key: bytes) -> dict[str, Any]:
    metadata = envelope.get("metadata") or {}
    if (
        metadata.get("shard_id") != GOLD_LABEL_CACHE_SHARD_ID
        or metadata.get("split") != "dev"
        or metadata.get("model_revision") != "gold-labels"
    ):
        raise ValueError("envelope is not a DEV gold-label cache")
    cache = json.loads(decrypt_bytes(envelope, key=key))
    if cache.get("schema_version") != LABEL_SCHEMA_VERSION or cache.get("split") != "dev":
        raise ValueError("unsupported gold-label cache payload")
    if str(cache.get("source_run_id")) != str(metadata.get("run_id")):
        raise ValueError("gold-label cache payload does not match its envelope metadata")
    records = _unique_sorted(cache["records"], _clean_label_record, "gold-label cache")
    if len(records) != cache["record_count"]:
        raise ValueError("gold-label cache has an unexpected record count")
    cache["records"] = records
    return cache


def join_scores_with_gold(
    score_cache: dict[str, Any], label_cache: dict[str, Any]
) -> dict[str, Any]:
    """Join private predictions and labels in memory at evaluation time only."""
    if score_cache.get("split") != "dev" or label_cache.get("split") != "dev":
        raise ValueError("only DEV score and label caches may be joined")
    for field in ("source_run_id", "manifest_sha256", "record_count"):
        if score_cache.get(field) != label_cache.get(field):
            raise ValueError(f"score and gold-label cache {field} mismatch")
    labels = {row["record_id"]: row for row in label_cache["records"]}
    if len(labels) != score_cache["record_count"]:
        raise ValueError("gold-label cache record count mismatch")
    joined_models: dict[str, Any] = {}
    for model, entry in score_cache["models"].items():
        score_ids = {row["record_id"] for row in entry["records"]}
        if score_ids != set(labels):
            raise ValueError(f"gold labels do not cover the same records as {model}")
        records = []
        for score in entry["records"]:
            label = labels[score["record_id"]]
            if score["cohort"] != label["cohort"]:
                raise ValueError("score and gold-label cohort mismatch")
            records.append({**score, "gold": label["gold"]})
        joined_models[model] = {"protocol": entry.get("protocol"), "records": records}
    return {
        **score_cache,
        "models": joined_models,
        "record_fields": ["record_id", "cohort", "gold", "score"],
    }


def replay_calibration_v2(cache: dict[str, Any]) -> dict[str, Any]:
    """Recompute Calibration V2 from an evaluation-time joined cache."""
    from scripts.benchmarks.phase1b.calibration_v2.aggregate import calibration_v2_report

    rows = {
        model: [
            {
                "record_id": r["record_id"],
                "cohort": r["cohort"],
                "gold": r["gold"],
                "score": r["score"],
            }
            for r in entry["records"]
        ]
        for model, entry in cache["models"].items()
    }
    calibration = calibration_v2_report(rows)
    calibration_sha256 = sha256_bytes(canonical_json(calibration))
    expected = cache.get("calibration_v2_sha256")
    report = {
        "schema_version": "phase1b-dev-cache-replay-v2",
        "split": "dev",
        "experiment": "replay-calibration-v2",
        "source_run_id": cache["source_run_id"],
        "manifest_sha256": cache["manifest_sha256"],
        "record_count": cache["record_count"],
        "models": sorted(cache["models"]),
        "calibration_v2": calibration,
        "calibration_v2_sha256": calibration_sha256,
        "expected_calibration_v2_sha256": expected,
        "replay_matches_source": expected is not None and expected == calibration_sha256,
        "instance_level_output_published": False,
    }
    report["report_sha256"] = sha256_bytes(canonical_json(report))
    return report


def run_e3_fixed_rule_ensemble(cache: dict[str, Any]) -> dict[str, Any]:
    """E3 under DEC-024 option B; see scripts/benchmarks/phase1b/e3_ensemble.py."""
    from scripts.benchmarks.phase1b.e3_ensemble import run_e3

    return run_e3(cache)


EXPERIMENTS = {
    "replay-calibration-v2": replay_calibration_v2,
    "e3-fixed-rule-ensemble": run_e3_fixed_rule_ensemble,
}


def _decode_gold_key() -> bytes:
    raw = os.environ.get("PHASE1B_GOLD_LABEL_ENCRYPTION_KEY")
    if not raw:
        raise RuntimeError("PHASE1B_GOLD_LABEL_ENCRYPTION_KEY is required")
    return decode_key(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", required=True, type=Path, help="encrypted prediction cache")
    parser.add_argument(
        "--gold-labels",
        required=True,
        type=Path,
        help="separately encrypted gold-label cache",
    )
    parser.add_argument("--experiment", required=True, choices=sorted(EXPERIMENTS))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    score_key = decode_key()
    gold_key = _decode_gold_key()
    if score_key == gold_key:
        raise ValueError("gold-label and prediction encryption keys must be distinct")
    score_envelope = json.loads(args.cache.read_text(encoding="utf-8"))
    label_envelope = json.loads(args.gold_labels.read_text(encoding="utf-8"))
    scores = decrypt_score_cache(score_envelope, key=score_key)
    labels = decrypt_gold_label_cache(label_envelope, key=gold_key)
    score_metadata = score_envelope.get("metadata") or {}
    label_metadata = label_envelope.get("metadata") or {}
    for field in ("run_id", "split", "dataset_revision", "code_sha"):
        if score_metadata.get(field) != label_metadata.get(field):
            raise ValueError(f"score and gold-label envelope {field} differs")
    joined = join_scores_with_gold(scores, labels)
    report = EXPERIMENTS[args.experiment](joined)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(args.output, canonical_json(report) + b"\n")
    print(
        json.dumps(
            {
                "experiment": args.experiment,
                "split": "dev",
                "record_count": report["record_count"],
                "replay_matches_source": report.get("replay_matches_source"),
                "instance_level_output_published": False,
            },
            sort_keys=True,
        )
    )
    if report.get("replay_matches_source") is False:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
