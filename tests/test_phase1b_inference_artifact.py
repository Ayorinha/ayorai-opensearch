"""Synthetic-only tests for encryption of the shared DEV inference input."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from scripts.benchmarks.phase1b.inference_artifact import (
    decrypt_inference_file,
    encrypt_inference_file,
    inference_metadata,
)


def _manifest(plaintext: bytes) -> dict[str, str]:
    return {
        "split": "dev",
        "dataset_revision": "synthetic-dataset-revision",
        "code_sha": "synthetic-sha",
        "inference_dataset_sha256": hashlib.sha256(plaintext).hexdigest(),
    }


def test_shared_inference_artifact_roundtrip_hides_plaintext(tmp_path: Path) -> None:
    plaintext = b'{"record_id":"synthetic-id","doc":"synthetic private document"}\n'
    manifest = _manifest(plaintext)
    metadata = inference_metadata(manifest, run_id="synthetic-run", code_sha="synthetic-sha")
    source = tmp_path / "inference.jsonl"
    encrypted = tmp_path / "inference.jsonl.aesgcm"
    restored = tmp_path / "restored.jsonl"
    source.write_bytes(plaintext)
    key = bytes(range(32))

    encrypt_inference_file(
        source,
        encrypted,
        key=key,
        metadata=metadata,
        expected_sha256=manifest["inference_dataset_sha256"],
    )
    envelope_text = encrypted.read_text(encoding="utf-8")
    assert "synthetic private document" not in envelope_text
    assert "synthetic-id" not in envelope_text

    decrypt_inference_file(
        encrypted,
        restored,
        key=key,
        expected_metadata=metadata,
        expected_sha256=manifest["inference_dataset_sha256"],
    )
    assert restored.read_bytes() == plaintext


def test_shared_inference_artifact_rejects_changed_provenance(tmp_path: Path) -> None:
    plaintext = b'{"record_id":"synthetic-id"}\n'
    manifest = _manifest(plaintext)
    metadata = inference_metadata(manifest, run_id="synthetic-run", code_sha="synthetic-sha")
    source = tmp_path / "inference.jsonl"
    encrypted = tmp_path / "inference.jsonl.aesgcm"
    source.write_bytes(plaintext)
    key = bytes(range(32))
    encrypt_inference_file(
        source,
        encrypted,
        key=key,
        metadata=metadata,
        expected_sha256=manifest["inference_dataset_sha256"],
    )

    changed = dict(metadata, code_sha="different-sha")
    with pytest.raises(ValueError, match="metadata does not match"):
        decrypt_inference_file(
            encrypted,
            tmp_path / "out.jsonl",
            key=key,
            expected_metadata=changed,
            expected_sha256=manifest["inference_dataset_sha256"],
        )


def test_shared_inference_artifact_rejects_wrong_key(tmp_path: Path) -> None:
    plaintext = b'{"record_id":"synthetic-id"}\n'
    manifest = _manifest(plaintext)
    metadata = inference_metadata(manifest, run_id="synthetic-run", code_sha="synthetic-sha")
    source = tmp_path / "inference.jsonl"
    encrypted = tmp_path / "inference.jsonl.aesgcm"
    source.write_bytes(plaintext)
    encrypt_inference_file(
        source,
        encrypted,
        key=bytes(range(32)),
        metadata=metadata,
        expected_sha256=manifest["inference_dataset_sha256"],
    )

    with pytest.raises(InvalidTag):
        decrypt_inference_file(
            encrypted,
            tmp_path / "out.jsonl",
            key=bytes(reversed(range(32))),
            expected_metadata=metadata,
            expected_sha256=manifest["inference_dataset_sha256"],
        )


def test_inference_artifact_rejects_digest_mismatch_before_encryption(tmp_path: Path) -> None:
    source = tmp_path / "inference.jsonl"
    source.write_bytes(b'{"record_id":"unexpected"}\n')
    metadata = inference_metadata(
        _manifest(b'{"record_id":"expected"}\n'),
        run_id="synthetic-run",
        code_sha="synthetic-sha",
    )

    with pytest.raises(ValueError, match="does not match the encrypted manifest"):
        encrypt_inference_file(
            source,
            tmp_path / "inference.jsonl.aesgcm",
            key=bytes(range(32)),
            metadata=metadata,
            expected_sha256=hashlib.sha256(b'{"record_id":"expected"}\n').hexdigest(),
        )


def test_inference_artifact_rejects_digest_mismatch_after_decryption(tmp_path: Path) -> None:
    plaintext = b'{"record_id":"synthetic-id"}\n'
    manifest = _manifest(plaintext)
    metadata = inference_metadata(manifest, run_id="synthetic-run", code_sha="synthetic-sha")
    source = tmp_path / "inference.jsonl"
    encrypted = tmp_path / "inference.jsonl.aesgcm"
    source.write_bytes(plaintext)
    encrypt_inference_file(
        source,
        encrypted,
        key=bytes(range(32)),
        metadata=metadata,
        expected_sha256=manifest["inference_dataset_sha256"],
    )

    with pytest.raises(ValueError, match="does not match the encrypted manifest"):
        decrypt_inference_file(
            encrypted,
            tmp_path / "out.jsonl",
            key=bytes(range(32)),
            expected_metadata=metadata,
            expected_sha256="0" * 64,
        )
    assert not (tmp_path / "out.jsonl").exists()


def test_shared_inference_metadata_rejects_code_sha_mismatch() -> None:
    with pytest.raises(ValueError, match="code SHA does not match"):
        inference_metadata(
            _manifest(b"synthetic"),
            run_id="synthetic-run",
            code_sha="different-sha",
        )


def test_shared_inference_metadata_rejects_non_dev_manifest() -> None:
    with pytest.raises(ValueError, match="only DEV"):
        inference_metadata(
            {"split": "test", "dataset_revision": "synthetic"},
            run_id="synthetic-run",
            code_sha="synthetic-sha",
        )


def test_shared_inference_metadata_rejects_missing_or_invalid_digest() -> None:
    for digest in (None, "not-a-digest", "a" * 63, "G" * 64):
        manifest = {
            "split": "dev",
            "dataset_revision": "synthetic-dataset-revision",
            "code_sha": "synthetic-sha",
            "inference_dataset_sha256": digest,
        }
        with pytest.raises(ValueError, match="digest is invalid or unavailable"):
            inference_metadata(manifest, run_id="synthetic-run", code_sha="synthetic-sha")
