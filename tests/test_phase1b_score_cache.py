"""A1 — separate encrypted DEV predictions and gold labels.

Synthetic data only. The end-to-end test executes the aggregator and replay CLIs
exactly as the workflow does, and verifies that the joined evaluation replay
reproduces the aggregate without storing gold labels in the score cache.
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
    GOLD_LABEL_CACHE_SHARD_ID,
    SCORE_CACHE_SHARD_ID,
    build_gold_label_cache,
    build_score_cache,
    decrypt_gold_label_cache,
    decrypt_score_cache,
    encrypt_gold_label_cache,
    encrypt_score_cache,
    join_scores_with_gold,
)
from tests.test_phase1b_aggregate_cli import _run_aggregator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCORE_CACHE = REPOSITORY_ROOT / "scripts" / "benchmarks" / "phase1b" / "score_cache.py"
SCORE_KEY = bytes(range(32))
GOLD_KEY = bytes(reversed(range(32)))


def _rows(scores: list[float]) -> list[dict]:
    return [
        {
            "record_id": f"rid-{index:03d}",
            "cohort": "cohort-a",
            "gold": "SUPPORTED" if index % 2 else "NOT_SUPPORTED",
            "score": score,
            "claim": "SYNTHETIC text that must never reach either cache",
        }
        for index, score in enumerate(scores)
    ]


def _score_rows(rows: list[dict]) -> list[dict]:
    return [{"record_id": r["record_id"], "cohort": r["cohort"], "score": r["score"]} for r in rows]


def _labels(rows: list[dict]) -> list[dict]:
    return [{"record_id": r["record_id"], "cohort": r["cohort"], "gold": r["gold"]} for r in rows]


def _caches() -> tuple[dict, dict]:
    raw_a = _rows([0.1, 0.9, 0.2])
    raw_b = _rows([0.3, 0.7, 0.4])
    scores = build_score_cache(
        {"model-a": _score_rows(raw_a), "model-b": _score_rows(raw_b)},
        protocols={"model-a": {"name": "p"}, "model-b": {"name": "q"}},
        manifest_sha256="m" * 64,
        source_run_id="123",
        source_code_sha="source-code-sha",
        calibration_v2={"synthetic": True},
    )
    labels = build_gold_label_cache(_labels(raw_a), manifest_sha256="m" * 64, source_run_id="123")
    return scores, labels


def test_prediction_cache_contains_no_gold_or_text() -> None:
    scores, labels = _caches()
    serialized_scores = json.dumps(scores)
    assert "gold" not in serialized_scores.lower()
    assert "SUPPORTED" not in serialized_scores
    assert "SYNTHETIC text" not in serialized_scores
    assert scores["record_count"] == labels["record_count"] == 3
    assert scores["calibration_v2_sha256"] is not None
    assert scores["record_fields"] == ["record_id", "cohort", "score"]


def test_score_cache_requires_source_code_sha() -> None:
    with pytest.raises(ValueError, match="source_code_sha is required"):
        build_score_cache(
            {"model-a": _score_rows(_rows([0.1]))},
            protocols={},
            manifest_sha256="m" * 64,
            source_run_id="1",
            source_code_sha="",
            calibration_v2=None,
        )
    scores, _ = _caches()
    scores_without_source_sha = dict(scores)
    scores_without_source_sha.pop("source_code_sha")
    with pytest.raises(ValueError, match="source_code_sha is missing"):
        encrypt_score_cache(
            scores_without_source_sha,
            key=SCORE_KEY,
            dataset_revision="rev",
            code_sha="aggregate-code-sha",
        )


def test_score_cache_rejects_gold_labels_at_construction() -> None:
    with pytest.raises(ValueError, match="gold labels must never"):
        build_score_cache(
            {"model-a": _rows([0.1])},
            protocols={},
            manifest_sha256="m",
            source_run_id="1",
            source_code_sha="source-code-sha",
            calibration_v2=None,
        )


def test_separate_envelopes_round_trip_and_authenticate_metadata() -> None:
    scores, labels = _caches()
    score_envelope = encrypt_score_cache(
        scores, key=SCORE_KEY, dataset_revision="rev", code_sha="aggregate-code-sha"
    )
    label_envelope = encrypt_gold_label_cache(
        labels, key=GOLD_KEY, dataset_revision="rev", code_sha="source-code-sha"
    )
    assert score_envelope["metadata"]["shard_id"] == SCORE_CACHE_SHARD_ID
    assert label_envelope["metadata"]["shard_id"] == GOLD_LABEL_CACHE_SHARD_ID
    assert score_envelope["metadata"]["code_sha"] == "synthetic-aggregate-code-sha"
    assert label_envelope["metadata"]["code_sha"] == "synthetic-code-sha"
    assert decrypt_score_cache(score_envelope, key=SCORE_KEY)["source_code_sha"] == "synthetic-code-sha"
    assert score_envelope["metadata"] != label_envelope["metadata"]
    assert "rid-000" not in json.dumps(score_envelope)
    assert "rid-000" not in json.dumps(label_envelope)
    assert decrypt_score_cache(score_envelope, key=SCORE_KEY)["record_count"] == 3
    assert decrypt_gold_label_cache(label_envelope, key=GOLD_KEY)["record_count"] == 3

    tampered_score = dict(score_envelope, metadata=dict(score_envelope["metadata"], run_id="999"))
    tampered_labels = dict(label_envelope, metadata=dict(label_envelope["metadata"], run_id="999"))
    with pytest.raises(InvalidTag):
        decrypt_score_cache(tampered_score, key=SCORE_KEY)
    with pytest.raises(InvalidTag):
        decrypt_gold_label_cache(tampered_labels, key=GOLD_KEY)
    with pytest.raises(InvalidTag):
        decrypt_score_cache(score_envelope, key=GOLD_KEY)
    with pytest.raises(InvalidTag):
        decrypt_gold_label_cache(label_envelope, key=SCORE_KEY)


def test_join_occurs_only_after_both_caches_are_decrypted() -> None:
    scores, labels = _caches()
    joined = join_scores_with_gold(scores, labels)
    assert joined["models"]["model-a"]["records"][0]["gold"] in {"SUPPORTED", "NOT_SUPPORTED"}
    assert "gold" not in json.dumps(scores)
    assert "gold" in json.dumps(labels)


def test_join_rejects_run_manifest_count_and_cohort_mismatches() -> None:
    scores, labels = _caches()
    with pytest.raises(ValueError, match="source_run_id mismatch"):
        join_scores_with_gold(scores, {**labels, "source_run_id": "other"})
    bad_records = [
        dict(labels["records"][0], cohort="other"),
        *labels["records"][1:],
    ]
    bad_labels = dict(labels, records=bad_records)
    with pytest.raises(ValueError, match="cohort mismatch"):
        join_scores_with_gold(scores, bad_labels)


@pytest.mark.parametrize("mismatch", ["run_id", "dataset_revision", "source_code_sha"])
def test_replay_rejects_valid_envelopes_with_mismatched_provenance(
    tmp_path: Path, mismatch: str
) -> None:
    scores, labels = _caches()
    label_run_id = "123"
    score_revision = "rev"
    label_revision = "rev"
    score_code_sha = "aggregate-code"
    label_code_sha = "source-code-sha"
    if mismatch == "run_id":
        label_run_id = "other-run"
        labels = build_gold_label_cache(
            _labels(_rows([0.1, 0.9, 0.2])),
            manifest_sha256="m" * 64,
            source_run_id=label_run_id,
        )
    elif mismatch == "dataset_revision":
        label_revision = "other-revision"
    else:
        label_code_sha = "source-code-b"
    score_envelope = encrypt_score_cache(
        scores, key=SCORE_KEY, dataset_revision=score_revision, code_sha=score_code_sha
    )
    label_envelope = encrypt_gold_label_cache(
        labels, key=GOLD_KEY, dataset_revision=label_revision, code_sha=label_code_sha
    )
    score_path = tmp_path / "score.json"
    label_path = tmp_path / "labels.json"
    output_path = tmp_path / "report.json"
    score_path.write_text(json.dumps(score_envelope), encoding="utf-8")
    label_path.write_text(json.dumps(label_envelope), encoding="utf-8")
    env = {
        "PHASE1B_ARTIFACT_ENCRYPTION_KEY": base64.b64encode(SCORE_KEY).decode(),
        "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY": base64.b64encode(GOLD_KEY).decode(),
    }
    completed = subprocess.run(
        [
            sys.executable,
            str(SCORE_CACHE),
            "--cache",
            str(score_path),
            "--gold-labels",
            str(label_path),
            "--experiment",
            "replay-calibration-v2",
            "--output",
            str(output_path),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    expected_error = (
        "source_code_sha does not match gold-label source code_sha"
        if mismatch == "source_code_sha"
        else f"envelope {mismatch} differs"
    )
    assert expected_error in completed.stderr
    assert not output_path.exists()


def test_cache_rejects_non_dev_payload() -> None:
    scores, labels = _caches()
    with pytest.raises(ValueError, match="DEV"):
        encrypt_score_cache(
            dict(scores, split="test"), key=SCORE_KEY, dataset_revision="rev", code_sha="sha"
        )
    with pytest.raises(ValueError, match="DEV"):
        encrypt_gold_label_cache(
            dict(labels, split="test"), key=GOLD_KEY, dataset_revision="rev", code_sha="sha"
        )


def test_cli_cache_and_replay_reproduce_calibration_v2(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache" / "phase1b-dev-score-cache.json"
    completed, output_path, context = _run_aggregator(
        tmp_path, "--score-cache-output", str(cache_path), "--code-sha", "synthetic-aggregate-code-sha"
    )
    assert completed.returncode == 0, completed.stderr
    aggregate = json.loads(output_path.read_text())
    labels_path = context["gold_label_cache_path"]
    score_envelope = json.loads(cache_path.read_text())
    label_envelope = json.loads(labels_path.read_text())
    assert score_envelope["metadata"]["shard_id"] == SCORE_CACHE_SHARD_ID
    assert label_envelope["metadata"]["shard_id"] == GOLD_LABEL_CACHE_SHARD_ID
    assert score_envelope["metadata"]["code_sha"] == "synthetic-aggregate-code-sha"
    assert label_envelope["metadata"]["code_sha"] == "synthetic-code-sha"
    assert decrypt_score_cache(score_envelope, key=SCORE_KEY)["source_code_sha"] == "synthetic-code-sha"
    assert "gold" not in json.dumps(decrypt_score_cache(score_envelope, key=SCORE_KEY)).lower()
    assert not any(record_id in cache_path.read_text() for record_id in context["rows_by_id"])
    assert not any(record_id in labels_path.read_text() for record_id in context["rows_by_id"])

    replay_path = tmp_path / "replay.json"
    replay = subprocess.run(
        [
            sys.executable,
            str(SCORE_CACHE),
            "--cache",
            str(cache_path),
            "--gold-labels",
            str(labels_path),
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
        env={
            "PHASE1B_ARTIFACT_ENCRYPTION_KEY": base64.b64encode(SCORE_KEY).decode(),
            "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY": base64.b64encode(GOLD_KEY).decode(),
            "PATH": "",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "--score-cache-output requires --calibration-v2" in completed.stderr
