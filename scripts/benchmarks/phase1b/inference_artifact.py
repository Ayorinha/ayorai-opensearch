#!/usr/bin/env python3
"""Encrypt and decrypt the shared DEV inference input artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .common import atomic_write_bytes
    from .encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes
except ImportError:  # direct script execution
    from common import atomic_write_bytes
    from encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes


def inference_metadata(manifest: dict[str, Any], *, run_id: str, code_sha: str) -> dict[str, str]:
    if manifest.get("split") != "dev":
        raise ValueError("only DEV inference inputs may be encrypted")
    dataset_revision = manifest.get("dataset_revision")
    if not isinstance(dataset_revision, str) or not dataset_revision:
        raise ValueError("DEV manifest dataset_revision is required")
    if not run_id or not code_sha:
        raise ValueError("run_id and code_sha are required")
    if manifest.get("code_sha") != code_sha:
        raise ValueError("inference artifact code SHA does not match DEV manifest")
    return {
        "run_id": run_id,
        "split": "dev",
        "model_revision": "shared-inference-v1",
        "shard_id": "all",
        "dataset_revision": dataset_revision,
        "code_sha": code_sha,
    }


def encrypt_inference_file(
    input_path: Path,
    output_path: Path,
    *,
    key: bytes,
    metadata: dict[str, str],
) -> None:
    envelope = encrypt_bytes(input_path.read_bytes(), key=key, metadata=metadata)
    atomic_write_bytes(output_path, json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def decrypt_inference_file(
    input_path: Path,
    output_path: Path,
    *,
    key: bytes,
    expected_metadata: dict[str, str],
) -> None:
    envelope = json.loads(input_path.read_text(encoding="utf-8"))
    if envelope.get("schema_version") != "phase1b-aes256gcm-v1":
        raise ValueError("unsupported encrypted inference artifact schema")
    if envelope.get("metadata") != expected_metadata:
        raise ValueError("encrypted inference metadata does not match expected provenance")
    plaintext = decrypt_bytes(envelope, key=key, aad_metadata=expected_metadata)
    atomic_write_bytes(output_path, plaintext)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("encrypt", "decrypt"))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--code-sha", required=True)
    args = parser.parse_args()

    key = decode_key()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    metadata = inference_metadata(manifest, run_id=args.run_id, code_sha=args.code_sha)
    if args.mode == "encrypt":
        encrypt_inference_file(args.input, args.output, key=key, metadata=metadata)
        print(json.dumps({"status": "encrypted", "split": "dev", "artifact": "shared-inference"}))
    else:
        decrypt_inference_file(args.input, args.output, key=key, expected_metadata=metadata)
        print(json.dumps({"status": "decrypted", "split": "dev", "artifact": "shared-inference"}))


if __name__ == "__main__":
    main()
