#!/usr/bin/env python3
"""Emit a GitHub Actions matrix from a DEV manifest only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from .common import (
        MANIFEST_SCHEMA_VERSION,
        RECORD_ID_METHOD,
        SHARD_ID_PATTERN,
        canonical_json,
        sha256_bytes,
    )
except ImportError:  # direct script execution
    _REPOSITORY_ROOT = str(Path(__file__).resolve().parents[3])
    if _REPOSITORY_ROOT not in sys.path:
        sys.path.insert(0, _REPOSITORY_ROOT)
    from scripts.benchmarks.phase1b.common import (
        MANIFEST_SCHEMA_VERSION,
        RECORD_ID_METHOD,
        SHARD_ID_PATTERN,
        canonical_json,
        sha256_bytes,
    )


def emit_matrix(manifest: dict, *, minimal: bool = False) -> dict:
    if (
        manifest.get("split") != "dev"
        or manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or manifest.get("record_id_method") != RECORD_ID_METHOD
    ):
        raise ValueError("matrix generation requires a current inference-only DEV manifest")
    manifest_body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest.get("manifest_sha256") != sha256_bytes(canonical_json(manifest_body)):
        raise ValueError("DEV manifest digest verification failed")
    shards = manifest.get("shards")
    if not isinstance(shards, list) or not shards:
        raise ValueError("manifest has no shards")
    shard_ids = [item.get("shard_id") if isinstance(item, dict) else None for item in shards]
    if any(
        not isinstance(shard_id, str) or re.fullmatch(SHARD_ID_PATTERN, shard_id) is None
        for shard_id in shard_ids
    ) or len(set(shard_ids)) != len(shard_ids):
        raise ValueError("manifest shard IDs are invalid or duplicated")
    if minimal:
        if len(shards) != 2 or any(item.get("count") != 5 for item in shards):
            raise ValueError("minimal mode requires exactly two shards of five examples")
    return {
        "split": "dev",
        "shard_ids": shard_ids,
        "model_ids": ["mdeberta"] if minimal else ["mdeberta", "minicheck", "factcg"],
        "matrix_enabled": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--minimal", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    matrix = emit_matrix(manifest, minimal=args.minimal)
    encoded = json.dumps(matrix, sort_keys=True, separators=(",", ":"))
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(f"phase1b_matrix={encoded}\n")
    print(
        json.dumps(
            {
                "status": "matrix_emitted",
                "shards": len(matrix["shard_ids"]),
                "split": "dev",
            }
        )
    )


if __name__ == "__main__":
    main()
