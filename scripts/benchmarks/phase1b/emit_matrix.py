#!/usr/bin/env python3
"""Emit a GitHub Actions matrix from a DEV manifest only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def emit_matrix(manifest: dict, *, minimal: bool = False) -> dict:
    if manifest.get("split") != "dev":
        raise ValueError("matrix generation is DEV-only")
    shards = manifest.get("shards")
    if not isinstance(shards, list) or not shards:
        raise ValueError("manifest has no shards")
    if minimal:
        if len(shards) != 1 or shards[0].get("count") != 10:
            raise ValueError("minimal mode requires exactly one shard of ten examples")
    return {
        "split": "dev",
        "shard_ids": [item["shard_id"] for item in shards],
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
    matrix = emit_matrix(json.loads(args.manifest.read_text(encoding="utf-8")), minimal=args.minimal)
    encoded = json.dumps(matrix, sort_keys=True, separators=(",", ":"))
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(f"phase1b_matrix={encoded}\n")
    print(json.dumps({"status": "matrix_emitted", "shards": len(matrix["shard_ids"]), "split": "dev"}))


if __name__ == "__main__":
    main()
