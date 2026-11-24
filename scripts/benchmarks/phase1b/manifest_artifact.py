#!/usr/bin/env python3
"""Encrypt and decrypt the DEV manifest so per-record identifiers stay private."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .common import DEV_PIN_PATH, MANIFEST_SCHEMA_VERSION, canonical_json, sha256_bytes
    from .encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes
except ImportError:  # direct script execution
    from common import DEV_PIN_PATH, MANIFEST_SCHEMA_VERSION, canonical_json, sha256_bytes
    from encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes

MANIFEST_ARTIFACT_SCHEMA = "phase1b-dev-manifest-aes256gcm-v1"
MANIFEST_MODEL_REVISION = "shared-dev-manifest-v1"


def _pinned_dataset() -> dict[str, str]:
    pin = json.loads(DEV_PIN_PATH.read_text(encoding="utf-8"))
    revision, digest = pin.get("revision"), pin.get("sha256")
    if not isinstance(revision, str) or not revision:
        raise ValueError("pinned DEV dataset revision is unavailable")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("pinned DEV dataset digest is unavailable")
    return {"revision": revision, "sha256": digest}


def validate_manifest(manifest: dict[str, Any], *, code_sha: str) -> None:
    if (
        manifest.get("split") != "dev"
        or manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
    ):
        raise ValueError("only current DEV manifests may be encrypted or decrypted")
    pin = _pinned_dataset()
    if manifest.get("dataset_revision") != pin["revision"]:
        raise ValueError("DEV manifest dataset revision does not match the immutable pin")
    if manifest.get("dataset_sha256") != pin["sha256"]:
        raise ValueError("DEV manifest dataset digest does not match the immutable pin")
    if not code_sha or manifest.get("code_sha") != code_sha:
        raise ValueError("DEV manifest code SHA does not match expected provenance")
    shards = manifest.get("shards")
    if not isinstance(shards, list) or not shards:
        raise ValueError("DEV manifest must contain at least one shard")
    shard_ids: set[str] = set()
    record_ids: set[str] = set()
    total_records = 0
    for shard in shards:
        if not isinstance(shard, dict):
            raise ValueError("DEV manifest shard must be an object")
        shard_id = shard.get("shard_id")
        ids = shard.get("record_ids")
        count = shard.get("count")
        if not isinstance(shard_id, str) or not shard_id or shard_id in shard_ids:
            raise ValueError("DEV manifest shard identity is invalid or duplicated")
        if not isinstance(ids, list) or not isinstance(count, int) or count != len(ids):
            raise ValueError("DEV manifest shard record count is inconsistent")
        if any(not isinstance(record_id, str) or len(record_id) != 64 for record_id in ids):
            raise ValueError("DEV manifest contains an invalid record identifier")
        if len(set(ids)) != len(ids) or record_ids.intersection(ids):
            raise ValueError("DEV manifest contains duplicate record identifiers")
        if shard.get("record_ids_sha256") != sha256_bytes(canonical_json(ids)):
            raise ValueError("DEV manifest shard record digest verification failed")
        shard_ids.add(shard_id)
        record_ids.update(ids)
        total_records += count
    if manifest.get("sample_count") != total_records:
        raise ValueError("DEV manifest total record count is inconsistent")
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    expected = sha256_bytes(canonical_json(body))
    if manifest.get("manifest_sha256") != expected:
        raise ValueError("DEV manifest digest verification failed")


def manifest_metadata(*, run_id: str, code_sha: str) -> dict[str, str]:
    if not run_id or not code_sha:
        raise ValueError("run_id and code_sha are required")
    return {
        "run_id": run_id,
        "split": "dev",
        "model_revision": MANIFEST_MODEL_REVISION,
        "shard_id": "all",
        "dataset_revision": _pinned_dataset()["revision"],
        "code_sha": code_sha,
    }


def encrypt_manifest_file(
    input_path: Path,
    output_path: Path,
    *,
    key: bytes,
    metadata: dict[str, str],
) -> None:
    manifest = json.loads(input_path.read_text(encoding="utf-8"))
    validate_manifest(manifest, code_sha=metadata["code_sha"])
    if manifest["dataset_revision"] != metadata["dataset_revision"]:
        raise ValueError("manifest dataset revision does not match envelope metadata")
    envelope = encrypt_bytes(canonical_json(manifest), key=key, metadata=metadata)
    envelope["artifact_schema"] = MANIFEST_ARTIFACT_SCHEMA
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(envelope, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def decrypt_manifest_file(
    input_path: Path,
    output_path: Path,
    *,
    key: bytes,
    expected_metadata: dict[str, str],
) -> None:
    envelope = json.loads(input_path.read_text(encoding="utf-8"))
    if envelope.get("artifact_schema") != MANIFEST_ARTIFACT_SCHEMA:
        raise ValueError("unsupported encrypted DEV manifest schema")
    if envelope.get("schema_version") != "phase1b-aes256gcm-v1":
        raise ValueError("unsupported AES-256-GCM envelope schema")
    if set(envelope) != {
        "artifact_schema", "schema_version", "metadata", "nonce_b64", "ciphertext_b64"
    }:
        raise ValueError("encrypted DEV manifest envelope has unexpected fields")
    if envelope.get("metadata") != expected_metadata:
        raise ValueError("encrypted DEV manifest metadata does not match expected provenance")
    plaintext = decrypt_bytes(envelope, key=key, aad_metadata=expected_metadata)
    manifest = json.loads(plaintext)
    validate_manifest(manifest, code_sha=expected_metadata["code_sha"])
    if manifest["dataset_revision"] != expected_metadata["dataset_revision"]:
        raise ValueError("decrypted DEV manifest dataset revision mismatch")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json(manifest) + b"\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("encrypt", "decrypt"))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--code-sha", required=True)
    args = parser.parse_args()

    key = decode_key()
    metadata = manifest_metadata(run_id=args.run_id, code_sha=args.code_sha)
    if args.mode == "encrypt":
        encrypt_manifest_file(args.input, args.output, key=key, metadata=metadata)
        print(json.dumps({"status": "encrypted", "split": "dev", "artifact": "manifest"}))
    else:
        decrypt_manifest_file(args.input, args.output, key=key, expected_metadata=metadata)
        print(json.dumps({"status": "decrypted", "split": "dev", "artifact": "manifest"}))


if __name__ == "__main__":
    main()
