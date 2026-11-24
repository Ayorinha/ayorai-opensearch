#!/usr/bin/env python3
"""Split the pinned DEV source into inference-only data and encrypted gold labels.

This preparation step runs before model inference. The inference artifact contains
only record_id, document, claim and cohort. Gold labels are written to a separate
AES-256-GCM envelope using PHASE1B_GOLD_LABEL_ENCRYPTION_KEY.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    from .common import (
        MANIFEST_SCHEMA_VERSION,
        RECORD_ID_METHOD,
        atomic_write_bytes,
        canonical_json,
        load_records,
        sha256_bytes,
        sha256_file,
        stable_record_id,
    )
    from .encrypt_artifact import decode_key
    from .score_cache import build_gold_label_cache, encrypt_gold_label_cache
except ImportError:  # direct script execution
    import sys

    _REPOSITORY_ROOT = str(Path(__file__).resolve().parents[3])
    if _REPOSITORY_ROOT not in sys.path:
        sys.path.insert(0, _REPOSITORY_ROOT)
    from scripts.benchmarks.phase1b.common import (
        MANIFEST_SCHEMA_VERSION,
        RECORD_ID_METHOD,
        atomic_write_bytes,
        canonical_json,
        load_records,
        sha256_bytes,
        sha256_file,
        stable_record_id,
    )
    from scripts.benchmarks.phase1b.encrypt_artifact import decode_key
    from scripts.benchmarks.phase1b.score_cache import (
        build_gold_label_cache,
        encrypt_gold_label_cache,
    )


def prepare(
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    source_run_id: str,
    code_sha: str,
    gold_key: bytes,
    inference_output: Path,
    gold_label_output: Path,
) -> dict[str, Any]:
    if (
        manifest.get("split") != "dev"
        or manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or manifest.get("record_id_method") != RECORD_ID_METHOD
    ):
        raise ValueError("only current inference-only DEV manifests may be prepared")
    manifest_body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest.get("manifest_sha256") != sha256_bytes(canonical_json(manifest_body)):
        raise ValueError("source DEV manifest digest verification failed")
    if manifest.get("code_sha") != code_sha:
        raise ValueError("manifest code SHA does not match preparation code SHA")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        record_id = stable_record_id(row)
        if record_id in indexed:
            raise ValueError("duplicate content-addressed DEV row")
        if str(row.get("label")) not in {"0", "1"}:
            raise ValueError("DEV label is outside the frozen binary mapping")
        indexed[record_id] = row

    selected_ids = [
        record_id
        for shard in manifest.get("shards", [])
        for record_id in shard.get("record_ids", [])
    ]
    if len(selected_ids) != manifest.get("sample_count") or len(set(selected_ids)) != len(
        selected_ids
    ):
        raise ValueError("manifest record coverage is inconsistent")
    if set(selected_ids) - set(indexed):
        raise ValueError("manifest contains records absent from pinned DEV source")

    inference_rows = []
    gold_rows = []
    for record_id in sorted(selected_ids):
        row = indexed[record_id]
        inference_rows.append(
            {
                "record_id": record_id,
                "doc": str(row["doc"]),
                "claim": str(row["claim"]),
                "dataset": str(row["dataset"]),
            }
        )
        gold_rows.append(
            {
                "record_id": record_id,
                "cohort": str(row["dataset"]),
                "gold": "SUPPORTED" if str(row["label"]) == "1" else "NOT_SUPPORTED",
            }
        )

    inference_output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(
        inference_output,
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in inference_rows
        ).encode("utf-8"),
    )
    manifest = dict(manifest)
    manifest["inference_dataset_sha256"] = sha256_file(inference_output)
    manifest.pop("manifest_sha256", None)
    manifest["manifest_sha256"] = sha256_bytes(canonical_json(manifest))

    labels = build_gold_label_cache(
        gold_rows,
        manifest_sha256=manifest["manifest_sha256"],
        source_run_id=source_run_id,
    )
    envelope = encrypt_gold_label_cache(
        labels,
        key=gold_key,
        dataset_revision=str(manifest["dataset_revision"]),
        code_sha=code_sha,
    )
    atomic_write_bytes(
        gold_label_output,
        json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset-path", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--inference-output", required=True, type=Path)
    parser.add_argument("--gold-label-cache-output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--code-sha", required=True)
    args = parser.parse_args()

    raw_key = os.environ.get("PHASE1B_GOLD_LABEL_ENCRYPTION_KEY")
    if not raw_key:
        raise RuntimeError("PHASE1B_GOLD_LABEL_ENCRYPTION_KEY is required")
    gold_key = decode_key(raw_key)
    score_key = decode_key()
    if gold_key == score_key:
        raise ValueError("gold-label and prediction encryption keys must be distinct")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if sha256_file(args.dataset_path) != manifest.get("dataset_sha256"):
        raise ValueError("source DEV dataset SHA-256 does not match the manifest")
    prepared = prepare(
        load_records(args.dataset_path),
        manifest,
        source_run_id=args.run_id,
        code_sha=args.code_sha,
        gold_key=gold_key,
        inference_output=args.inference_output,
        gold_label_output=args.gold_label_cache_output,
    )
    atomic_write_bytes(args.manifest, canonical_json(prepared) + b"\n")
    print(
        json.dumps(
            {
                "status": "dev_inputs_separated",
                "split": "dev",
                "record_count": prepared["sample_count"],
                "manifest_sha256": prepared["manifest_sha256"],
                "inference_dataset_sha256": prepared["inference_dataset_sha256"],
                "gold_labels_encrypted": True,
                "labels_in_inference_input": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
