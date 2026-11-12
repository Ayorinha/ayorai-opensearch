#!/usr/bin/env python3
"""Encrypted per-instance DEV score cache (roadmap v0.8, item A1).

The aggregate job already decrypts every shard in the protected environment. This
module keeps the per-instance scores it decrypted — and nothing else — in one
AES-256-GCM envelope, so later DEV experiments (calibration replays, fixed-rule
ensembles) can run in minutes without repeating inference.

Privacy contract:
- only whitelisted fields per record are kept: ``record_id`` (a stable hash, not
  dataset text), ``cohort``, ``gold`` and ``score``; schema v2 adds ``doc_id`` (a hash
  of cohort and document, never the text) so experiments can resample whole documents;
- the cache is DEV-only; TEST is rejected;
- the plaintext never leaves the protected job; only the encrypted envelope is
  uploaded, and experiment outputs are aggregates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from .common import canonical_json, sha256_bytes
    from .encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes
except ImportError:  # direct script execution
    _REPOSITORY_ROOT = str(Path(__file__).resolve().parents[3])
    if _REPOSITORY_ROOT not in sys.path:
        sys.path.insert(0, _REPOSITORY_ROOT)
    from common import canonical_json, sha256_bytes
    from encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes

SCHEMA_VERSION = "phase1b-dev-score-cache-v1"
SCHEMA_VERSION_V2 = "phase1b-dev-score-cache-v2"
CACHE_SHARD_ID = "dev-score-cache"
RECORD_FIELDS = ("record_id", "cohort", "gold", "score")
RECORD_FIELDS_V2 = (*RECORD_FIELDS, "doc_id")
FIELDS_BY_SCHEMA = {SCHEMA_VERSION: RECORD_FIELDS, SCHEMA_VERSION_V2: RECORD_FIELDS_V2}
GOLD_VALUES = frozenset({"SUPPORTED", "NOT_SUPPORTED"})
_HEX64 = re.compile(r"[0-9a-f]{64}")


def _clean_record(
    record: dict[str, Any], fields: tuple[str, ...] = RECORD_FIELDS
) -> dict[str, Any]:
    missing = [field for field in fields if field not in record]
    if missing:
        raise ValueError(f"score record is missing fields: {missing}")
    record_id = record["record_id"]
    cohort = record["cohort"]
    gold = record["gold"]
    score = record["score"]
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("record_id must be a non-empty string")
    if not isinstance(cohort, str) or not cohort:
        raise ValueError("cohort must be a non-empty string")
    if gold not in GOLD_VALUES:
        raise ValueError("gold must be SUPPORTED or NOT_SUPPORTED")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("score must be numeric")
    if not math.isfinite(float(score)) or not 0.0 <= float(score) <= 1.0:
        raise ValueError("score must be finite and within [0, 1]")
    cleaned = {"record_id": record_id, "cohort": cohort, "gold": gold, "score": float(score)}
    if "doc_id" in fields:
        doc_id = record["doc_id"]
        if not isinstance(doc_id, str) or not _HEX64.fullmatch(doc_id):
            raise ValueError("doc_id must be a 64-character lowercase hex digest")
        cleaned["doc_id"] = doc_id
    return cleaned


def _validated_rows(
    rows: list[dict[str, Any]], fields: tuple[str, ...] = RECORD_FIELDS
) -> list[dict[str, Any]]:
    cleaned = [_clean_record(record, fields) for record in rows]
    ids = [record["record_id"] for record in cleaned]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate record_id in one model")
    return sorted(cleaned, key=lambda record: record["record_id"])


def build_score_cache(
    rows_by_model: dict[str, list[dict[str, Any]]],
    *,
    protocols: dict[str, Any],
    manifest_sha256: str,
    source_run_id: str,
    calibration_v2: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the plaintext cache payload (kept in memory, then encrypted)."""

    if not rows_by_model:
        raise ValueError("score cache requires at least one model")
    models: dict[str, Any] = {}
    reference_ids: set[str] | None = None
    for model in sorted(rows_by_model):
        records = _validated_rows(rows_by_model[model])
        ids = {record["record_id"] for record in records}
        if reference_ids is None:
            reference_ids = ids
        elif ids != reference_ids:
            raise ValueError("all models must cover the same DEV records")
        models[model] = {"protocol": protocols.get(model), "records": records}
    return {
        "schema_version": SCHEMA_VERSION,
        "split": "dev",
        "source_run_id": str(source_run_id),
        "manifest_sha256": manifest_sha256,
        "record_count": len(reference_ids or ()),
        "record_fields": list(RECORD_FIELDS),
        "calibration_v2_sha256": (
            sha256_bytes(canonical_json(calibration_v2)) if calibration_v2 is not None else None
        ),
        "models": models,
    }


def _cache_metadata(cache: dict[str, Any], *, dataset_revision: str, code_sha: str) -> dict:
    return {
        "run_id": cache["source_run_id"],
        "split": "dev",
        "model_revision": "multi-model-score-cache",
        "shard_id": CACHE_SHARD_ID,
        "dataset_revision": dataset_revision,
        "code_sha": code_sha,
    }


def encrypt_score_cache(
    cache: dict[str, Any], *, key: bytes, dataset_revision: str, code_sha: str
) -> dict[str, Any]:
    if cache.get("schema_version") not in FIELDS_BY_SCHEMA or cache.get("split") != "dev":
        raise ValueError("only DEV score caches may be encrypted")
    metadata = _cache_metadata(cache, dataset_revision=dataset_revision, code_sha=code_sha)
    return encrypt_bytes(canonical_json(cache), key=key, metadata=metadata)


def decrypt_score_cache(envelope: dict[str, Any], *, key: bytes) -> dict[str, Any]:
    metadata = envelope.get("metadata") or {}
    if metadata.get("shard_id") != CACHE_SHARD_ID or metadata.get("split") != "dev":
        raise ValueError("envelope is not a DEV score cache")
    cache = json.loads(decrypt_bytes(envelope, key=key))
    fields = FIELDS_BY_SCHEMA.get(cache.get("schema_version"))
    if fields is None or cache.get("split") != "dev":
        raise ValueError("unsupported score cache payload")
    if str(cache.get("source_run_id")) != str(metadata.get("run_id")):
        raise ValueError("score cache payload does not match its envelope metadata")
    for model, entry in cache["models"].items():
        records = _validated_rows(entry["records"], fields)
        if len(records) != cache["record_count"]:
            raise ValueError(f"score cache for {model} has an unexpected record count")
        entry["records"] = records
    return cache


def replay_calibration_v2(cache: dict[str, Any]) -> dict[str, Any]:
    """Recompute Calibration V2 from the cache; must match the original aggregate."""

    from scripts.benchmarks.phase1b.calibration_v2.aggregate import calibration_v2_report

    rows = {
        model: [{field: record[field] for field in RECORD_FIELDS} for record in entry["records"]]
        for model, entry in cache["models"].items()
    }
    calibration = calibration_v2_report(rows)
    calibration_sha256 = sha256_bytes(canonical_json(calibration))
    expected = cache.get("calibration_v2_sha256")
    report = {
        "schema_version": "phase1b-dev-cache-replay-v1",
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


def run_e3_confirm_dev_b(cache: dict[str, Any]) -> dict[str, Any]:
    """P1 under DEC-024 option B and DEC-025; see scripts/benchmarks/phase1b/e3_confirm.py."""

    from scripts.benchmarks.phase1b.e3_confirm import run_confirm

    return run_confirm(cache)


EXPERIMENTS = {
    "replay-calibration-v2": replay_calibration_v2,
    "e3-fixed-rule-ensemble": run_e3_fixed_rule_ensemble,
    "e3-confirm-dev-b": run_e3_confirm_dev_b,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, help="encrypted cache envelope")
    parser.add_argument("--experiment", required=True, choices=sorted(EXPERIMENTS))
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="validate P1 authorization gates without reading or decrypting the score cache",
    )
    parser.add_argument(
        "--validate-cache-only",
        action="store_true",
        help="P1: decrypt and run the cache-level preflight; compute no DEV-B outcome",
    )
    parser.add_argument(
        "--reserve-lock",
        type=Path,
        metavar="RESERVATION_JSON",
        help="P1: reserve the single-use ref (hashes the envelope; never decrypts it)",
    )
    args = parser.parse_args()

    p1_modes = [args.preflight_only, args.validate_cache_only, args.reserve_lock is not None]
    if any(p1_modes) and args.experiment != "e3-confirm-dev-b":
        parser.error("P1 modes are available only for e3-confirm-dev-b")
    if sum(p1_modes) > 1:
        parser.error(
            "choose at most one of --preflight-only, --validate-cache-only, --reserve-lock"
        )

    if args.experiment == "e3-confirm-dev-b":
        from scripts.benchmarks.phase1b.e3_confirm import preflight_confirm

        preflight_confirm()

    if args.preflight_only:
        print(
            json.dumps(
                {"experiment": args.experiment, "preflight": "passed", "cache_accessed": False},
                sort_keys=True,
            )
        )
        return

    if args.cache is None:
        parser.error("--cache is required unless --preflight-only is used")
    envelope_bytes = args.cache.read_bytes()
    envelope_sha256 = hashlib.sha256(envelope_bytes).hexdigest()

    if args.reserve_lock is not None:
        from scripts.benchmarks.phase1b.e3_confirm import reserve_lock

        reservation = reserve_lock(args.reserve_lock, envelope_sha256)
        print(json.dumps({k: reservation[k] for k in ("ref", "sha", "run_id")}, sort_keys=True))
        return

    if args.output is None and not args.validate_cache_only:
        parser.error("--output is required to run an experiment")

    key = decode_key()
    envelope = json.loads(envelope_bytes.decode("utf-8"))
    cache = decrypt_score_cache(envelope, key=key)
    if args.validate_cache_only:
        from scripts.benchmarks.phase1b.e3_confirm import validate_cache

        result = validate_cache(cache)
        print(json.dumps({**result, "envelope_sha256": envelope_sha256}, sort_keys=True))
        return
    if args.experiment == "e3-confirm-dev-b":
        # Bind the reservation check to the bytes actually decrypted in this process.
        os.environ["P1_CACHE_ENVELOPE_SHA256"] = envelope_sha256
    try:
        report = EXPERIMENTS[args.experiment](cache)
    finally:
        os.environ.pop("P1_CACHE_ENVELOPE_SHA256", None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(report) + b"\n")
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
