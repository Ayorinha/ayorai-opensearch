"""Synthetic-only tests for Phase 1b. No LLM-AggreFact rows or labels are used."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts" / "benchmarks" / "phase1b"),
)

from aggregate_dev import aggregate_packages
from build_manifest import build_manifest
from common import stable_record_id
from encrypt_artifact import decode_key, decrypt_bytes, encrypt_bytes
from run_shard import select_shard


def synthetic_rows(count: int = 10) -> list[dict]:
    return [
        {
            "doc": f"SYNTHETIC document {index} with length " + ("x " * (index + 1)),
            "claim": f"SYNTHETIC claim {index}",
            "label": index % 2,
            "dataset": "SYNTHETIC-COHORT",
        }
        for index in range(count)
    ]


def manifest_for(rows: list[dict], shard_size: int = 10) -> dict:
    return build_manifest(
        rows,
        dataset_sha256="a" * 64,
        dataset_revision="synthetic-revision",
        code_sha="synthetic-code-sha",
        shard_size=shard_size,
        seed=7,
    )


def test_manifest_is_deterministic_and_contains_no_instance_text() -> None:
    rows = synthetic_rows()
    first = manifest_for(rows)
    second = manifest_for(list(reversed(rows)))
    assert first == second
    serialized = json.dumps(first)
    assert "SYNTHETIC document" not in serialized
    assert "SYNTHETIC claim" not in serialized
    assert all(
        len(record_id) == 64 for shard in first["shards"] for record_id in shard["record_ids"]
    )


def test_shards_are_exact_disjoint_and_complete() -> None:
    manifest = manifest_for(synthetic_rows(23), shard_size=10)
    shards = [shard["record_ids"] for shard in manifest["shards"]]
    flattened = [record_id for shard in shards for record_id in shard]
    assert [len(shard) for shard in shards] == [10, 10, 3]
    assert len(flattened) == len(set(flattened)) == 23
    assert set(flattened) == {stable_record_id(row) for row in synthetic_rows(23)}


def test_length_sorting_does_not_change_record_association() -> None:
    rows = synthetic_rows(10)
    manifest = manifest_for(rows)
    selected = select_shard(manifest, rows, "dev-0000")
    by_id = {record_id: row["claim"] for record_id, row in selected}
    reordered = sorted(selected, key=lambda item: (len(item[1]["doc"]), item[0]))
    assert {record_id: row["claim"] for record_id, row in reordered} == by_id
    assert [record_id for record_id, _ in reordered] != [record_id for record_id, _ in selected]


def test_encryption_roundtrip_and_wrong_aad_fails() -> None:
    key = bytes(range(32))
    metadata = {
        "run_id": "synthetic-run",
        "split": "dev",
        "model_revision": "synthetic-model-revision",
        "shard_id": "dev-0000",
        "dataset_revision": "synthetic-dataset-revision",
        "code_sha": "synthetic-code-sha",
    }
    plaintext = b'{"synthetic":"private payload"}'
    envelope = encrypt_bytes(plaintext, key=key, metadata=metadata, nonce=b"n" * 12)
    assert decrypt_bytes(envelope, key=key) == plaintext
    wrong = dict(metadata, shard_id="dev-9999")
    with pytest.raises(ValueError):
        decrypt_bytes(envelope, key=key, aad_metadata=wrong)


def test_missing_key_fails_before_payload_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PHASE1B_ARTIFACT_ENCRYPTION_KEY", raising=False)
    with pytest.raises(RuntimeError, match="PHASE1B_ARTIFACT_ENCRYPTION_KEY"):
        decode_key()


def test_aggregator_marks_missing_shard_as_incomplete() -> None:
    rows = synthetic_rows(20)
    manifest = build_manifest(
        rows,
        dataset_sha256="b" * 64,
        dataset_revision="synthetic",
        code_sha="synthetic",
        shard_size=10,
    )
    key = bytes(range(32))
    metadata = {
        "run_id": "run-1",
        "split": "dev",
        "model_revision": "model-rev",
        "shard_id": "dev-0000",
        "dataset_revision": "synthetic",
        "code_sha": "synthetic",
    }
    private = {
        "split": "dev",
        "shard_id": "dev-0000",
        "model_id": "synthetic-model",
        "records": [
            {
                "record_id": stable_record_id(row),
                "gold": "SUPPORTED" if row["label"] else "NOT_SUPPORTED",
                "score": 0.9 if row["label"] else 0.1,
            }
            for row in rows[:10]
        ],
    }
    envelope = encrypt_bytes(
        json.dumps(private).encode(),
        key=key,
        metadata=metadata,
        nonce=b"z" * 12,
    )
    report = aggregate_packages(manifest, [envelope], key=key)
    assert report["complete"] is False
    assert report["incomplete_models"] == [
        {"model_id": "synthetic-model", "missing_shard_count": 1}
    ]


def test_report_has_no_per_instance_output() -> None:
    rows = synthetic_rows(10)
    manifest = manifest_for(rows)
    key = bytes(range(32))
    metadata = {
        "run_id": "run-2",
        "split": "dev",
        "model_revision": "model-rev",
        "shard_id": "dev-0000",
        "dataset_revision": "synthetic-revision",
        "code_sha": "synthetic-code-sha",
    }
    private = {
        "split": "dev", "shard_id": "dev-0000", "model_id": "synthetic-model",
        "records": [
            {
                "record_id": stable_record_id(row),
                "gold": "SUPPORTED" if row["label"] else "NOT_SUPPORTED",
                "score": 0.9 if row["label"] else 0.1,
            }
            for row in rows
        ],
    }
    envelope = encrypt_bytes(
        json.dumps(private).encode(),
        key=key,
        metadata=metadata,
        nonce=b"q" * 12,
    )
    report = aggregate_packages(manifest, [envelope], key=key)
    public_json = json.dumps(report)
    assert report["complete"] is True
    assert "record_id" not in public_json
    assert "SYNTHETIC claim" not in public_json
    assert "records" not in public_json
