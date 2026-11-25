#!/usr/bin/env python3
"""Encrypt and decrypt the shared DEV inference input artifact."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from .common import atomic_write_bytes, sha256_bytes
    from .encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes
except ImportError:  # direct script execution
    from common import atomic_write_bytes, sha256_bytes
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
    inference_digest = manifest.get("inference_dataset_sha256")
    if (
        not isinstance(inference_digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", inference_digest) is None
    ):
        raise ValueError("DEV manifest inference dataset digest is invalid or unavailable")
    return {
        "run_id": run_id,
        "split": "dev",
        "model_revision": "shared-inference-v1",
        "shard_id": "all",
        "dataset_revision": dataset_revision,
        "code_sha": code_sha,
    }


def _verify_inference_digest(payload: bytes, expected_sha256: str) -> None:
    if not isinstance(expected_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise ValueError("expected inference dataset digest must be a SHA-256 hex digest")
    if sha256_bytes(payload) != expected_sha256:
        raise ValueError("inference dataset SHA-256 does not match the encrypted manifest")


def encrypt_inference_file(
    input_path: Path,
    output_path: Path,
    *,
    key: bytes,
    metadata: dict[str, str],
    expected_sha256: str,
) -> None:
    plaintext = input_path.read_bytes()
    _verify_inference_digest(plaintext, expected_sha256)
    envelope = encrypt_bytes(plaintext, key=key, metadata=metadata)
    atomic_write_bytes(
        output_path,
        json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    )


def decrypt_inference_file(
    input_path: Path,
    output_path: Path,
    *,
    key: bytes,
    expected_metadata: dict[str, str],
    expected_sha256: str,
) -> None:
    envelope = json.loads(input_path.read_text(encoding="utf-8"))
    if envelope.get("schema_version") != "phase1b-aes256gcm-v1":
        raise ValueError("unsupported encrypted inference artifact schema")
    if envelope.get("metadata") != expected_metadata:
        raise ValueError("encrypted inference metadata does not match expected provenance")
    plaintext = decrypt_bytes(envelope, key=key, aad_metadata=expected_metadata)
    _verify_inference_digest(plaintext, expected_sha256)
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
    expected_sha256 = manifest["inference_dataset_sha256"]
    if args.mode == "encrypt":
        encrypt_inference_file(
            args.input, args.output, key=key, metadata=metadata, expected_sha256=expected_sha256
        )
        print(json.dumps({"status": "encrypted", "split": "dev", "artifact": "shared-inference"}))
    else:
        decrypt_inference_file(
            args.input,
            args.output,
            key=key,
            expected_metadata=metadata,
            expected_sha256=expected_sha256,
        )
        print(json.dumps({"status": "decrypted", "split": "dev", "artifact": "shared-inference"}))


if __name__ == "__main__":
    main()
