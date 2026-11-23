"""Synthetic-only tests for pre-inference separation of DEV inputs and gold labels."""

from __future__ import annotations

import json

import pytest

from scripts.benchmarks.phase1b.build_manifest import build_manifest
from scripts.benchmarks.phase1b.common import canonical_json, sha256_bytes, stable_record_id
from scripts.benchmarks.phase1b.prepare_dev_artifacts import prepare
from scripts.benchmarks.phase1b.score_cache import decrypt_gold_label_cache

GOLD_KEY = bytes(reversed(range(32)))


def _rows() -> list[dict]:
    return [
        {
            "doc": f"SYNTHETIC document {index}",
            "claim": f"SYNTHETIC claim {index}",
            "label": index % 2,
            "dataset": "SYNTHETIC-COHORT",
        }
        for index in range(12)
    ]


def _manifest(rows: list[dict]) -> dict:
    return build_manifest(
        rows,
        dataset_sha256="a" * 64,
        dataset_revision="synthetic-revision",
        code_sha="synthetic-code-sha",
        shard_size=5,
        seed=7,
    )


def test_preparation_removes_labels_before_model_inference(tmp_path) -> None:
    rows = _rows()
    manifest = _manifest(rows)
    inference_path = tmp_path / "inference" / "dev.jsonl"
    labels_path = tmp_path / "labels" / "gold.json"
    prepared = prepare(
        rows,
        manifest,
        source_run_id="synthetic-run",
        code_sha="synthetic-code-sha",
        gold_key=GOLD_KEY,
        inference_output=inference_path,
        gold_label_output=labels_path,
    )

    inference_rows = [
        json.loads(line) for line in inference_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(inference_rows) == len(rows)
    assert all(set(row) == {"record_id", "doc", "claim", "dataset"} for row in inference_rows)
    serialized = json.dumps(inference_rows)
    assert '"label"' not in serialized and '"gold"' not in serialized
    assert "SUPPORTED" not in serialized and "NOT_SUPPORTED" not in serialized
    assert prepared["inference_dataset_sha256"]
    assert prepared["manifest_sha256"] != manifest["manifest_sha256"]

    envelope = json.loads(labels_path.read_text(encoding="utf-8"))
    assert "SYNTHETIC" not in json.dumps(envelope)
    labels = decrypt_gold_label_cache(envelope, key=GOLD_KEY)
    assert labels["record_count"] == len(rows)
    assert {item["record_id"] for item in labels["records"]} == {
        stable_record_id(row) for row in rows
    }


def test_preparation_fails_closed_on_wrong_code_or_missing_manifest_record(tmp_path) -> None:
    rows = _rows()
    manifest = _manifest(rows)
    with pytest.raises(ValueError, match="code SHA"):
        prepare(
            rows,
            manifest,
            source_run_id="run",
            code_sha="wrong",
            gold_key=GOLD_KEY,
            inference_output=tmp_path / "inference.jsonl",
            gold_label_output=tmp_path / "labels.json",
        )

    truncated = dict(manifest)
    truncated["shards"] = [dict(manifest["shards"][0], record_ids=["f" * 64], count=1)]
    truncated["sample_count"] = 1
    truncated.pop("manifest_sha256")
    truncated["manifest_sha256"] = sha256_bytes(canonical_json(truncated))
    with pytest.raises(ValueError, match="absent"):
        prepare(
            rows,
            truncated,
            source_run_id="run",
            code_sha="synthetic-code-sha",
            gold_key=GOLD_KEY,
            inference_output=tmp_path / "inference.jsonl",
            gold_label_output=tmp_path / "labels.json",
        )


def test_preparation_rejects_non_dev_manifest(tmp_path) -> None:
    with pytest.raises(ValueError, match="DEV"):
        prepare(
            _rows(),
            dict(_manifest(_rows()), split="test"),
            source_run_id="run",
            code_sha="synthetic-code-sha",
            gold_key=GOLD_KEY,
            inference_output=tmp_path / "inference.jsonl",
            gold_label_output=tmp_path / "labels.json",
        )
