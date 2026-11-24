"""Synthetic-only tests for encryption of the DEV manifest artifact."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from scripts.benchmarks.phase1b.common import MANIFEST_SCHEMA_VERSION, canonical_json, sha256_bytes
from scripts.benchmarks.phase1b.manifest_artifact import (
    decrypt_manifest_file,
    encrypt_manifest_file,
    manifest_metadata,
)

KEY = bytes(range(32))


def _manifest() -> dict:
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "split": "dev",
        "dataset": "SYNTHETIC",
        "dataset_revision": "synthetic-pinned-revision",
        "dataset_sha256": "a" * 64,
        "code_sha": "synthetic-code-sha",
        "sample_count": 2,
        "shards": [
            {
                "shard_id": "dev-0000",
                "count": 2,
                "record_ids": ["b" * 64, "c" * 64],
            }
        ],
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical_json(manifest))
    return manifest


def _metadata(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setattr(
        "scripts.benchmarks.phase1b.manifest_artifact._pinned_dataset_revision",
        lambda: "synthetic-pinned-revision",
    )
    return manifest_metadata(run_id="synthetic-run", code_sha="synthetic-code-sha")


def test_manifest_artifact_roundtrip_hides_record_ids(tmp_path: Path, monkeypatch) -> None:
    manifest = _manifest()
    source = tmp_path / "manifest.json"
    encrypted = tmp_path / "manifest.json.aesgcm"
    restored = tmp_path / "restored.json"
    source.write_text(json.dumps(manifest), encoding="utf-8")
    metadata = _metadata(monkeypatch)

    encrypt_manifest_file(source, encrypted, key=KEY, metadata=metadata)
    envelope = encrypted.read_text(encoding="utf-8")
    assert "b" * 64 not in envelope
    assert "c" * 64 not in envelope
    assert "record_ids" not in envelope

    decrypt_manifest_file(encrypted, restored, key=KEY, expected_metadata=metadata)
    assert json.loads(restored.read_text(encoding="utf-8")) == manifest


def test_manifest_artifact_rejects_changed_provenance(tmp_path: Path, monkeypatch) -> None:
    manifest = _manifest()
    source = tmp_path / "manifest.json"
    encrypted = tmp_path / "manifest.json.aesgcm"
    source.write_text(json.dumps(manifest), encoding="utf-8")
    metadata = _metadata(monkeypatch)
    encrypt_manifest_file(source, encrypted, key=KEY, metadata=metadata)

    changed = dict(metadata, code_sha="different-code-sha")
    with pytest.raises(ValueError, match="metadata does not match"):
        decrypt_manifest_file(
            encrypted,
            tmp_path / "restored.json",
            key=KEY,
            expected_metadata=changed,
        )


def test_manifest_artifact_rejects_wrong_key(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "manifest.json"
    encrypted = tmp_path / "manifest.json.aesgcm"
    source.write_text(json.dumps(_manifest()), encoding="utf-8")
    metadata = _metadata(monkeypatch)
    encrypt_manifest_file(source, encrypted, key=KEY, metadata=metadata)

    with pytest.raises(InvalidTag):
        decrypt_manifest_file(
            encrypted,
            tmp_path / "restored.json",
            key=bytes(reversed(range(32))),
            expected_metadata=metadata,
        )


def test_manifest_artifact_rejects_tampered_manifest_digest(tmp_path: Path, monkeypatch) -> None:
    manifest = _manifest()
    manifest["shards"][0]["record_ids"][0] = "d" * 64
    source = tmp_path / "manifest.json"
    source.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="digest verification failed"):
        encrypt_manifest_file(
            source,
            tmp_path / "manifest.json.aesgcm",
            key=KEY,
            metadata=_metadata(monkeypatch),
        )


def test_manifest_artifact_rejects_non_dev_manifest(tmp_path: Path, monkeypatch) -> None:
    manifest = _manifest()
    manifest["split"] = "test"
    manifest.pop("manifest_sha256")
    manifest["manifest_sha256"] = sha256_bytes(canonical_json(manifest))
    source = tmp_path / "manifest.json"
    source.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="only current DEV"):
        encrypt_manifest_file(
            source,
            tmp_path / "manifest.json.aesgcm",
            key=KEY,
            metadata=_metadata(monkeypatch),
        )
