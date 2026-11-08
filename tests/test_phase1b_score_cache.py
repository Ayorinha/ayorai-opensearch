"""A1 — encrypted DEV score cache: privacy whitelist, integrity and replay fidelity.

Synthetic data only. The end-to-end test runs both scripts by file path, exactly as the
workflows do, and checks that a Calibration V2 replay from the cache reproduces the
original aggregate bit for bit.
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from scripts.benchmarks.phase1b.score_cache import (
    CACHE_SHARD_ID,
    RECORD_FIELDS,
    build_score_cache,
    decrypt_score_cache,
    encrypt_score_cache,
)
from tests.test_phase1b_aggregate_cli import _run_aggregator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCORE_CACHE = REPOSITORY_ROOT / "scripts" / "benchmarks" / "phase1b" / "score_cache.py"
KEY = bytes(range(32))


def _rows(scores: list[float]) -> list[dict]:
    return [
        {
            "record_id": f"rid-{index:03d}",
            "cohort": "cohort-a",
            "gold": "SUPPORTED" if index % 2 else "NOT_SUPPORTED",
            "score": score,
            "claim": "SYNTHETIC text that must never reach the cache",
        }
        for index, score in enumerate(scores)
    ]


def _cache() -> dict:
    return build_score_cache(
        {"model-a": _rows([0.1, 0.9, 0.2]), "model-b": _rows([0.3, 0.7, 0.4])},
        protocols={"model-a": {"name": "p"}, "model-b": {"name": "q"}},
        manifest_sha256="m" * 64,
        source_run_id="123",
        calibration_v2={"synthetic": True},
    )


def test_cache_keeps_only_whitelisted_fields() -> None:
    cache = _cache()
    for entry in cache["models"].values():
        for record in entry["records"]:
            assert tuple(record) == RECORD_FIELDS
    assert "SYNTHETIC text" not in json.dumps(cache)
    assert cache["record_count"] == 3
    assert cache["calibration_v2_sha256"] is not None


def test_cache_round_trip_and_tamper_detection() -> None:
    envelope = encrypt_score_cache(_cache(), key=KEY, dataset_revision="rev", code_sha="sha")
    assert envelope["metadata"]["shard_id"] == CACHE_SHARD_ID
    assert "rid-000" not in json.dumps(envelope)
    assert decrypt_score_cache(envelope, key=KEY)["models"]["model-a"]["records"][0]["score"] == 0.1

    tampered = dict(envelope, metadata=dict(envelope["metadata"], run_id="999"))
    with pytest.raises(InvalidTag):
        decrypt_score_cache(tampered, key=KEY)
    with pytest.raises(InvalidTag):
        decrypt_score_cache(envelope, key=bytes(32))


@pytest.mark.parametrize(
    ("rows_by_model", "message"),
    [
        ({"a": _rows([1.5])}, "within"),
        ({"a": _rows([0.2, 0.2])[:1] * 2}, "duplicate"),
        ({"a": _rows([0.2, 0.3]), "b": _rows([0.2])}, "same DEV records"),
        ({"a": [{"record_id": "x", "cohort": "c", "gold": "MAYBE", "score": 0.5}]}, "gold"),
    ],
)
def test_cache_rejects_invalid_rows(rows_by_model: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_score_cache(
            rows_by_model,
            protocols={},
            manifest_sha256="m",
            source_run_id="1",
            calibration_v2=None,
        )


def test_cache_rejects_non_dev_payload() -> None:
    cache = dict(_cache(), split="test")
    with pytest.raises(ValueError, match="DEV"):
        encrypt_score_cache(cache, key=KEY, dataset_revision="rev", code_sha="sha")


def test_cli_cache_and_replay_reproduce_calibration_v2(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache" / "phase1b-dev-score-cache.json"
    completed, output_path, context = _run_aggregator(
        tmp_path, "--score-cache-output", str(cache_path), "--code-sha", "synthetic-code-sha"
    )
    assert completed.returncode == 0, completed.stderr
    aggregate = json.loads(output_path.read_text())
    envelope_text = cache_path.read_text()
    assert not any(record_id in envelope_text for record_id in context["rows_by_id"])

    replay_path = tmp_path / "replay.json"
    replay = subprocess.run(
        [
            sys.executable,
            str(SCORE_CACHE),
            "--cache",
            str(cache_path),
            "--experiment",
            "replay-calibration-v2",
            "--output",
            str(replay_path),
        ],
        cwd=tmp_path,
        env=context["env"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert replay.returncode == 0, replay.stderr
    report = json.loads(replay_path.read_text())
    assert report["replay_matches_source"] is True
    assert report["calibration_v2"] == aggregate["calibration_v2"]
    serialized = json.dumps(report)
    assert "record_id" not in serialized
    assert not any(record_id in serialized for record_id in context["rows_by_id"])


def test_score_cache_output_requires_calibration_v2(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY_ROOT / "scripts" / "benchmarks" / "phase1b" / "aggregate_dev.py"),
            "--manifest",
            "m.json",
            "--encrypted-dir",
            ".",
            "--output",
            "o.json",
            "--score-cache-output",
            "c.json",
        ],
        cwd=tmp_path,
        env={"PHASE1B_ARTIFACT_ENCRYPTION_KEY": base64.b64encode(KEY).decode(), "PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "requires --calibration-v2" in completed.stderr
