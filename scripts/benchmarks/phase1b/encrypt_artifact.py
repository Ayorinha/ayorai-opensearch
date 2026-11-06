#!/usr/bin/env python3
"""AES-256-GCM encryption for private DEV shard packages."""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AAD_FIELDS = ("run_id", "split", "model_revision", "shard_id", "dataset_revision", "code_sha")


def decode_key(value: str | None = None) -> bytes:
    raw = value if value is not None else os.environ.get("PHASE1B_ARTIFACT_ENCRYPTION_KEY")
    if not raw:
        raise RuntimeError("PHASE1B_ARTIFACT_ENCRYPTION_KEY is required")
    try:
        key = base64.b64decode(raw, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("encryption key must be valid Base64") from exc
    if len(key) != 32:
        raise ValueError("encryption key must decode to exactly 32 bytes")
    return key


def build_aad(metadata: dict[str, Any]) -> bytes:
    if any(field not in metadata or metadata[field] in (None, "") for field in AAD_FIELDS):
        raise ValueError("AAD metadata is incomplete")
    if metadata["split"] != "dev":
        raise ValueError("only DEV artifacts may be encrypted by this workflow")
    return json.dumps({key: metadata[key] for key in AAD_FIELDS}, sort_keys=True, separators=(",", ":")).encode()


def encrypt_bytes(plaintext: bytes, *, key: bytes, metadata: dict[str, Any], nonce: bytes | None = None) -> dict[str, Any]:
    if len(key) != 32:
        raise ValueError("AES-256 key must contain 32 bytes")
    nonce_value = nonce if nonce is not None else secrets.token_bytes(12)
    if len(nonce_value) != 12:
        raise ValueError("AES-GCM nonce must contain 12 bytes")
    ciphertext = AESGCM(key).encrypt(nonce_value, plaintext, build_aad(metadata))
    return {
        "schema_version": "phase1b-aes256gcm-v1",
        "metadata": {field: metadata[field] for field in AAD_FIELDS},
        "nonce_b64": base64.b64encode(nonce_value).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_bytes(envelope: dict[str, Any], *, key: bytes, aad_metadata: dict[str, Any] | None = None) -> bytes:
    metadata = aad_metadata if aad_metadata is not None else envelope["metadata"]
    aad = build_aad(metadata)
    if metadata != envelope["metadata"]:
        raise ValueError("AAD metadata mismatch")
    nonce = base64.b64decode(envelope["nonce_b64"], validate=True)
    ciphertext = base64.b64decode(envelope["ciphertext_b64"], validate=True)
    return AESGCM(key).decrypt(nonce, ciphertext, aad)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--shard-id", required=True)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--code-sha", required=True)
    args = parser.parse_args()
    # Resolve the key before reading or parsing the private payload.
    key = decode_key()
    package = json.loads(args.input.read_text(encoding="utf-8"))
    metadata = {
        "run_id": args.run_id,
        "split": "dev",
        "model_revision": args.model_revision,
        "shard_id": args.shard_id,
        "dataset_revision": args.dataset_revision,
        "code_sha": args.code_sha,
    }
    if package.get("split") != "dev" or package.get("shard_id") != args.shard_id:
        raise ValueError("private package metadata does not match requested encryption context")
    envelope = encrypt_bytes(args.input.read_bytes(), key=key, metadata=metadata)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(envelope, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"status": "encrypted", "split": "dev", "shard_id": args.shard_id}))


if __name__ == "__main__":
    main()
