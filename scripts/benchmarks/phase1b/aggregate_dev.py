#!/usr/bin/env python3
"""Decrypt DEV shard artifacts and publish operational-only aggregate metadata."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from .common import canonical_json, sha256_bytes
    from .encrypt_artifact import decode_key, decrypt_bytes
except ImportError:  # direct script execution
    from common import canonical_json, sha256_bytes
    from encrypt_artifact import decode_key, decrypt_bytes


OPERATIONAL_FIELDS = (
    "document_count",
    "block_count",
    "token_count_by_unit",
    "tokenization_seconds",
    "inference_seconds",
    "total_seconds",
    "peak_ram_bytes",
    "truncation_count",
    "failure_count",
    "encryption_seconds",
    "decryption_seconds",
)


def aggregate_packages(
    manifest: dict[str, Any],
    encrypted_packages: list[dict[str, Any]],
    *,
    key: bytes,
    calibration_v2: bool = False,
) -> dict[str, Any]:
    """Validate encrypted shard provenance and aggregate operational metadata only."""
    if manifest.get("split") != "dev":
        raise ValueError("aggregator accepts DEV manifests only")
    manifest_body = {
        key_name: value for key_name, value in manifest.items() if key_name != "manifest_sha256"
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
        shard_id = private.get("shard_id")
        model_id = private.get("model_id")
        if metadata.get("shard_id") != shard_id or metadata.get("model_revision") != private.get(
            "model_revision"
        ):
            raise ValueError(
                "encrypted artifact metadata does not match private package"
            )
        if metadata.get("dataset_revision") != private.get("dataset_revision") or metadata.get(
            "code_sha"
        ) != private.get("code_sha"):
            raise ValueError("encrypted artifact provenance mismatch")
        if (
            private.get("dataset_sha256") != manifest.get("dataset_sha256")
            or private.get("dataset_revision") != manifest.get("dataset_revision")
            or private.get("code_sha") != manifest.get("code_sha")
        ):
            raise ValueError("encrypted artifact manifest provenance mismatch")
        if shard_id not in expected:
            raise ValueError("unexpected shard artifact")

        expected_count = expected[shard_id]["count"]
        if private.get("document_count") != expected_count:
            raise ValueError("operational document count does not match shard manifest")
        if private.get("split") != "dev":
            raise ValueError("private package is not DEV-only")

        package_key = (str(model_id), str(shard_id))
        if package_key in packages:
            raise ValueError("duplicate model/shard artifact")
        packages[package_key] = private

    if len(run_ids) > 1:
        raise ValueError("encrypted artifacts belong to different workflow runs")

    models = sorted({model for model, _ in packages})
    summaries: dict[str, dict[str, Any]] = {}
    incomplete: list[dict[str, Any]] = []
    calibration_rows: dict[str, list[dict[str, Any]]] = {}

    for model in models:
        present = {shard for candidate, shard in packages if candidate == model}
        missing = sorted(set(expected) - present)
        if missing:
            incomplete.append({"model_id": model, "missing_shard_count": len(missing)})
            continue

        aggregate: dict[str, Any] = {
            "document_count": 0,
            "block_count": 0,
            "token_count_by_unit": defaultdict(int),
            "tokenization_seconds": 0.0,
            "inference_seconds": 0.0,
            "total_seconds": 0.0,
            "peak_ram_bytes": 0,
            "truncation_count": 0,
            "failure_count": 0,
            "encryption_seconds": 0.0,
            "decryption_seconds": 0.0,
        }
        protocols_seen = {
            canonical_json(packages[(model, shard_id)].get("protocol")) for shard_id in expected
        }
        if len(protocols_seen) != 1:
            raise ValueError(
                "shards of one model were produced with different protocols"
            )
        for shard_id in sorted(expected):
            package = packages[(model, shard_id)]
            for field in OPERATIONAL_FIELDS:
                value = package.get(field)
                if field == "token_count_by_unit":
                    if not isinstance(value, dict):
                        raise ValueError("token_count_by_unit must be an object")
                    for unit, count in value.items():
                        if not isinstance(count, int) or count < 0:
                            raise ValueError(
                                "token counts must be nonnegative integers"
                            )
                        aggregate[field][unit] += count
                elif field == "peak_ram_bytes":
                    if value is not None:
                        if not isinstance(value, int) or value < 0:
                            raise ValueError("peak RAM must be a nonnegative integer")
                        aggregate[field] = max(aggregate[field], value)
                elif value is not None:
                    if not isinstance(value, (int, float)) or value < 0:
                        raise ValueError(f"{field} must be nonnegative")
                    aggregate[field] += value
        aggregate["token_count_by_unit"] = dict(
            sorted(aggregate["token_count_by_unit"].items())
        )
        aggregate["protocol"] = packages[(model, sorted(expected)[0])].get("protocol")
        summaries[model] = aggregate
        if calibration_v2:
            calibration_rows[model] = [
                record
                for shard_id in sorted(expected)
                for record in packages[(model, shard_id)].get("records", [])
            ]

    report = {
        "schema_version": "phase1b-dev-operational-aggregate-v1",
        "split": "dev",
        "manifest_sha256": manifest.get("manifest_sha256"),
        "expected_shard_count": len(expected),
        "models": summaries,
        "incomplete_models": incomplete,
        "complete": not incomplete and bool(summaries),
        "quality_metrics": "not_computed_minimal_run",
        "instance_level_output_published": False,
    }
    if calibration_v2:
        if incomplete or not report["complete"]:
            raise ValueError(
                "Calibration V2 requires complete encrypted DEV shards for every model"
            )
        from scripts.benchmarks.phase1b.calibration_v2.aggregate import (
            calibration_v2_report,
        )

        report["calibration_v2"] = calibration_v2_report(calibration_rows)
        report["quality_metrics"] = "calibration_v2_aggregate_only"

    report["report_sha256"] = sha256_bytes(canonical_json(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--encrypted-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--calibration-v2",
        action="store_true",
        help=(
            "Opt-in V2 aggregate calibration; does not change the protected "
            "minimal workflow"
        ),
    )
    args = parser.parse_args()

    # Fail closed before opening encrypted artifacts if the secret is absent/invalid.
    key = decode_key()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    envelopes = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(args.encrypted_dir.glob("*.json"))
    ]
    report = aggregate_packages(
        manifest, envelopes, key=key, calibration_v2=args.calibration_v2
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(report) + b"\n")
    print(
        json.dumps(
            {
                "status": "complete" if report["complete"] else "incomplete",
                "split": "dev",
                "model_count": len(report["models"]),
                "incomplete_model_count": len(report["incomplete_models"]),
                "quality_metrics": report["quality_metrics"],
                "instance_level_output_published": False,
            },
            sort_keys=True,
        )
    )
    if not report["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
