"""Synthetic-only tests for encryption of the shared DEV inference input."""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from scripts.benchmarks.phase1b.inference_artifact import (
    decrypt_inference_file,
    encrypt_inference_file,
    inference_metadata,
)


def test_shared_inference_artifact_roundtrip_hides_plaintext(tmp_path: Path) -> None:
    manifest = {"split": "dev", "dataset_revision": "synthetic-dataset-revision"}
    metadata = inference_metadata(manifest, run_id="synthetic-run", code_sha="synthetic-sha")
    source = tmp_path / "inference.jsonl"
    encrypted = tmp_path / "inference.jsonl.aesgcm"
    restored = tmp_path / "restored.jsonl"
    plaintext = b'{"record_id":"synthetic-id","doc":"synthetic private document"}\n'
    source.write_bytes(plaintext)
    key = bytes(range(32))

    encrypt_inference_file(source, encrypted, key=key, metadata=metadata)
    envelope_text = encrypted.read_text(encoding="utf-8")
    assert "synthetic private document" not in envelope_text
    assert "synthetic-id" not in envelope_text

    decrypt_inference_file(encrypted, restored, key=key, expected_metadata=metadata)
    assert restored.read_bytes() == plaintext


def test_shared_inference_artifact_rejects_changed_provenance(tmp_path: Path) -> None:
    manifest = {"split": "dev", "dataset_revision": "synthetic-dataset-revision"}
    metadata = inference_metadata(manifest, run_id="synthetic-run", code_sha="synthetic-sha")
    source = tmp_path / "inference.jsonl"
    encrypted = tmp_path / "inference.jsonl.aesgcm"
    source.write_text('{"record_id":"synthetic-id"}\n', encoding="utf-8")
    key = bytes(range(32))
    encrypt_inference_file(source, encrypted, key=key, metadata=metadata)

    changed = dict(metadata, code_sha="different-sha")
    with pytest.raises(ValueError, match="metadata does not match"):
        decrypt_inference_file(encrypted, tmp_path / "out.jsonl", key=key, expected_metadata=changed)


def test_shared_inference_artifact_rejects_wrong_key(tmp_path: Path) -> None:
    manifest = {"split": "dev", "dataset_revision": "synthetic-dataset-revision"}
    metadata = inference_metadata(manifest, run_id="synthetic-run", code_sha="synthetic-sha")
    source = tmp_path / "inference.jsonl"
    encrypted = tmp_path / "inference.jsonl.aesgcm"
    source.write_bytes(b'{"record_id":"synthetic-id"}\n')
    encrypt_inference_file(source, encrypted, key=bytes(range(32)), metadata=metadata)

    with pytest.raises(InvalidTag):
        decrypt_inference_file(
            encrypted,
            tmp_path / "out.jsonl",
            key=bytes(reversed(range(32))),
            expected_metadata=metadata,
        )


def test_shared_inference_metadata_rejects_non_dev_manifest() -> None:
    with pytest.raises(ValueError, match="only DEV"):
        inference_metadata(
            {"split": "test", "dataset_revision": "synthetic"},
            run_id="synthetic-run",
            code_sha="synthetic-sha",
        )
