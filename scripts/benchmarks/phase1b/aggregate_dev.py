#!/usr/bin/env python3
"""Decrypt DEV shard artifacts and publish aggregate-only metrics."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from .common import canonical_json, sha256_bytes
    from .encrypt_artifact import decode_key, decrypt_bytes
except ImportError:  # direct script execution
    from common import canonical_json, sha256_bytes
    from encrypt_artifact import decode_key, decrypt_bytes


def aggregate_packages(
    manifest: dict[str, Any],
    encrypted_packages: list[dict[str, Any]],
    *,
    key: bytes,
) -> dict[str, Any]:
    if manifest.get("split") != "dev":
        raise ValueError("aggregator accepts DEV manifests only")
    manifest_body = {
        key_name: value
        for key_name, value in manifest.items()
        if key_name != "manifest_sha256"
    }
    expected_manifest_sha = sha256_bytes(canonical_json(manifest_body))
    if manifest.get("manifest_sha256") != expected_manifest_sha:
        raise ValueError("manifest digest verification failed")
    expected = {shard["shard_id"]: shard for shard in manifest["shards"]}
    packages: dict[tuple[str, str], dict[str, Any]] = {}
    run_ids: set[str] = set()
    for envelope in encrypted_packages:
        metadata = envelope.get("metadata", {})
        if metadata.get("split") != "dev":
            raise ValueError("non-DEV encrypted artifact rejected")
        run_id = metadata.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("encrypted artifact run identity is missing")
        run_ids.add(run_id)
        private = json.loads(decrypt_bytes(envelope, key=key))
        shard_id = private["shard_id"]
        model_id = private["model_id"]
        if (
            metadata.get("shard_id") != shard_id
            or metadata.get("model_revision") != private.get("model_revision")
        ):
            raise ValueError("encrypted artifact metadata does not match private package")
        if (
            metadata.get("dataset_revision") != private.get("dataset_revision")
            or metadata.get("code_sha") != private.get("code_sha")
        ):
            raise ValueError("encrypted artifact provenance mismatch")
        if (
            private.get("dataset_sha256") != manifest.get("dataset_sha256")
            or private.get("dataset_revision") != manifest.get("dataset_revision")
            or private.get("code_sha") != manifest.get("code_sha")
        ):
            raise ValueError("encrypted artifact manifest provenance mismatch")
        if shard_id not in expected:
            raise ValueError("unexpected shard artifact")
        records = private.get("records", [])
        expected_shard = expected[shard_id]
        expected_ids = set(expected_shard["record_ids"])
        actual_ids = [record.get("record_id") for record in records]
        if (
            len(records) != expected_shard["count"]
            or len(actual_ids) != len(set(actual_ids))
            or set(actual_ids) != expected_ids
        ):
            raise ValueError("shard artifact record identity/count mismatch")
        key_tuple = (model_id, shard_id)
        if key_tuple in packages:
            raise ValueError("duplicate model/shard artifact")
        for record in records:
            score = record.get("score")
            if (
                record.get("gold") not in {"SUPPORTED", "NOT_SUPPORTED"}
                or not isinstance(score, (int, float))
                or not math.isfinite(score)
                or not 0.0 <= score <= 1.0
            ):
                raise ValueError("private shard contains an invalid score or label")
        packages[key_tuple] = private

    if len(run_ids) > 1:
        raise ValueError("encrypted artifacts belong to different workflow runs")
    models = sorted({model for model, _ in packages})
    summaries = {}
    incomplete = []
    for model in models:
        present = {shard for candidate, shard in packages if candidate == model}
        missing = sorted(set(expected) - present)
        if missing:
            incomplete.append({"model_id": model, "missing_shard_count": len(missing)})
            continue
        counts: Counter[tuple[str, str]] = Counter()
        total = 0
        for shard_id in sorted(expected):
            for record in packages[(model, shard_id)]["records"]:
                gold = record["gold"]
                predicted = "SUPPORTED" if float(record["score"]) >= 0.5 else "NOT_SUPPORTED"
                counts[(gold, predicted)] += 1
                total += 1
        tp = counts[("SUPPORTED", "SUPPORTED")]
        fn = counts[("SUPPORTED", "NOT_SUPPORTED")]
        tn = counts[("NOT_SUPPORTED", "NOT_SUPPORTED")]
        fp = counts[("NOT_SUPPORTED", "SUPPORTED")]
        recall_pos = tp / (tp + fn) if tp + fn else None
        recall_neg = tn / (tn + fp) if tn + fp else None
        ba = (
            (recall_pos + recall_neg) / 2
            if recall_pos is not None and recall_neg is not None
            else None
        )
        summaries[model] = {
            "example_count": total,
            "balanced_accuracy_at_0_5": ba,
            "confusion_matrix": {
                "gold_supported_pred_supported": tp,
                "gold_supported_pred_not_supported": fn,
                "gold_not_supported_pred_supported": fp,
                "gold_not_supported_pred_not_supported": tn,
            },
        }
    report = {
        "schema_version": "phase1b-dev-aggregate-v1",
        "split": "dev",
        "manifest_sha256": manifest.get("manifest_sha256"),
        "expected_shard_count": len(expected),
        "models": summaries,
        "incomplete_models": incomplete,
        "complete": not incomplete and bool(summaries),
        "instance_level_output_published": False,
    }
    report["report_sha256"] = sha256_bytes(canonical_json(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--encrypted-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    # Fail closed before opening any encrypted artifact if the secret is absent/invalid.
    key = decode_key()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    envelopes = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(args.encrypted_dir.glob("*.json"))
    ]
    report = aggregate_packages(manifest, envelopes, key=key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(report) + b"\n")
    print(
        json.dumps(
            {
                "status": "complete" if report["complete"] else "incomplete",
                "split": "dev",
                "model_count": len(report["models"]),
                "incomplete_model_count": len(report["incomplete_models"]),
                "instance_level_output_published": False,
            },
            sort_keys=True,
        )
    )
    if not report["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
