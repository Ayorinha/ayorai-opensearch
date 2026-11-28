"""In-process coverage for Phase 1b aggregation and score-cache CLIs.

All fixtures are synthetic. These tests exercise the same entry points used by
the workflows while keeping the Python code under test in the pytest process,
so coverage.py can measure the critical CLI paths.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from scripts.benchmarks.phase1b import aggregate_dev, score_cache
from tests.test_phase1b_aggregate_cli import _write_synthetic_inputs


def _run_main(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    *argv: str,
) -> None:
    monkeypatch.setattr(sys, "argv", [module.__name__, *argv])
    module.main()


def _set_artifact_key(
    monkeypatch: pytest.MonkeyPatch,
    environment: dict[str, str],
) -> None:
    monkeypatch.setenv(
        "PHASE1B_ARTIFACT_ENCRYPTION_KEY",
        environment["PHASE1B_ARTIFACT_ENCRYPTION_KEY"],
    )


def test_minimal_aggregate_cli_needs_no_gold_key_or_gold_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest, encrypted_dir, environment, _, gold_cache = _write_synthetic_inputs(tmp_path)
    _set_artifact_key(monkeypatch, environment)
    monkeypatch.delenv("PHASE1B_GOLD_LABEL_ENCRYPTION_KEY", raising=False)
    gold_cache.unlink()

    output = tmp_path / "reports" / "minimal.json"
    _run_main(
        monkeypatch,
        aggregate_dev,
        "--manifest",
        str(manifest),
        "--encrypted-dir",
        str(encrypted_dir),
        "--output",
        str(output),
    )

    summary = json.loads(capsys.readouterr().out)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert summary["status"] == "complete"
    assert report["quality_metrics"] == "not_computed_minimal_run"
    assert report["instance_level_output_published"] is False
    serialized = json.dumps(report).lower()
    assert "gold" not in serialized
    assert "record_id" not in serialized


def test_aggregate_and_score_cache_replay_clis_run_in_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest, encrypted_dir, environment, _, gold_cache = _write_synthetic_inputs(tmp_path)
    _set_artifact_key(monkeypatch, environment)
    monkeypatch.setenv(
        "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY",
        environment["PHASE1B_GOLD_LABEL_ENCRYPTION_KEY"],
    )

    aggregate_output = tmp_path / "reports" / "aggregate.json"
    score_cache_output = tmp_path / "cache" / "score.json"
    _run_main(
        monkeypatch,
        aggregate_dev,
        "--manifest",
        str(manifest),
        "--encrypted-dir",
        str(encrypted_dir),
        "--output",
        str(aggregate_output),
        "--calibration-v2",
        "--gold-label-cache-input",
        str(gold_cache),
        "--score-cache-output",
        str(score_cache_output),
        "--code-sha",
        "synthetic-aggregate-code-sha",
    )

    aggregate_summary = json.loads(capsys.readouterr().out)
    aggregate_report = json.loads(aggregate_output.read_text(encoding="utf-8"))
    score_envelope = json.loads(score_cache_output.read_text(encoding="utf-8"))
    score_payload = score_cache.decrypt_score_cache(
        score_envelope,
        key=base64.b64decode(environment["PHASE1B_ARTIFACT_ENCRYPTION_KEY"]),
    )
    assert aggregate_summary["status"] == "complete"
    assert aggregate_report["quality_metrics"] == "calibration_v2_aggregate_only"
    assert score_envelope["metadata"]["shard_id"] == score_cache.SCORE_CACHE_SHARD_ID
    assert "records" not in score_envelope
    assert "record_id" not in score_envelope
    assert "gold" not in json.dumps(score_payload).lower()

    replay_output = tmp_path / "reports" / "replay.json"
    _run_main(
        monkeypatch,
        score_cache,
        "--cache",
        str(score_cache_output),
        "--gold-labels",
        str(gold_cache),
        "--experiment",
        "replay-calibration-v2",
        "--output",
        str(replay_output),
    )
    replay_summary = json.loads(capsys.readouterr().out)
    replay_report = json.loads(replay_output.read_text(encoding="utf-8"))
    assert replay_summary["experiment"] == "replay-calibration-v2"
    assert replay_report["replay_matches_source"] is True
    assert replay_report["calibration_v2"] == aggregate_report["calibration_v2"]
    assert "record_id" not in json.dumps(replay_report)


def test_aggregate_cli_rejects_gold_input_without_calibration_before_file_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "aggregate.json"
    with pytest.raises(SystemExit) as caught:
        _run_main(
            monkeypatch,
            aggregate_dev,
            "--manifest",
            str(tmp_path / "missing-manifest.json"),
            "--encrypted-dir",
            str(tmp_path / "missing-encrypted"),
            "--output",
            str(output),
            "--gold-label-cache-input",
            str(tmp_path / "missing-gold-cache.json"),
        )

    assert caught.value.code == 2
    assert not output.exists()


def test_score_cache_cli_rejects_identical_keys_before_file_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    monkeypatch.setenv("PHASE1B_ARTIFACT_ENCRYPTION_KEY", key)
    monkeypatch.setenv("PHASE1B_GOLD_LABEL_ENCRYPTION_KEY", key)
    output = tmp_path / "replay.json"

    with pytest.raises(ValueError, match="must be distinct"):
        _run_main(
            monkeypatch,
            score_cache,
            "--cache",
            str(tmp_path / "missing-score.json"),
            "--gold-labels",
            str(tmp_path / "missing-labels.json"),
            "--experiment",
            "replay-calibration-v2",
            "--output",
            str(output),
        )

    assert not output.exists()


def test_score_cache_cli_requires_gold_key_before_file_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    monkeypatch.setenv("PHASE1B_ARTIFACT_ENCRYPTION_KEY", key)
    monkeypatch.delenv("PHASE1B_GOLD_LABEL_ENCRYPTION_KEY", raising=False)
    output = tmp_path / "replay.json"

    with pytest.raises(RuntimeError, match="PHASE1B_GOLD_LABEL_ENCRYPTION_KEY"):
        _run_main(
            monkeypatch,
            score_cache,
            "--cache",
            str(tmp_path / "missing-score.json"),
            "--gold-labels",
            str(tmp_path / "missing-labels.json"),
            "--experiment",
            "replay-calibration-v2",
            "--output",
            str(output),
        )

    assert not output.exists()


def test_score_cache_builder_rejects_empty_and_inconsistent_model_coverage() -> None:
    kwargs = {
        "protocols": {},
        "manifest_sha256": "m" * 64,
        "source_run_id": "synthetic-run",
        "source_code_sha": "synthetic-code-sha",
        "calibration_v2": None,
    }
    with pytest.raises(ValueError, match="at least one model"):
        score_cache.build_score_cache({}, **kwargs)

    with pytest.raises(ValueError, match="same DEV records"):
        score_cache.build_score_cache(
            {
                "model-a": [{"record_id": "rid-a", "cohort": "cohort-a", "score": 0.25}],
                "model-b": [{"record_id": "rid-b", "cohort": "cohort-a", "score": 0.75}],
            },
            **kwargs,
        )


def test_score_cache_doc_id_is_validated_and_retained() -> None:
    kwargs = {
        "protocols": {},
        "manifest_sha256": "m" * 64,
        "source_run_id": "synthetic-run",
        "source_code_sha": "synthetic-code-sha",
        "calibration_v2": None,
    }
    doc_id = "a" * 64
    cache = score_cache.build_score_cache(
        {"model-a": [{"record_id": "rid-a", "cohort": "cohort-a", "score": 0.5, "doc_id": doc_id}]},
        **kwargs,
    )
    assert cache["models"]["model-a"]["records"][0]["doc_id"] == doc_id

    with pytest.raises(ValueError, match="64-character lowercase hex digest"):
        score_cache.build_score_cache(
            {
                "model-a": [
                    {
                        "record_id": "rid-a",
                        "cohort": "cohort-a",
                        "score": 0.5,
                        "doc_id": "A" * 64,
                    }
                ]
            },
            **kwargs,
        )


def test_score_cache_v4_decryption_rejects_records_without_doc_id() -> None:
    key = bytes(range(32))
    legacy_v4 = {
        "schema_version": score_cache.SCORE_CACHE_SCHEMA_V4,
        "split": "dev",
        "source_run_id": "synthetic-run",
        "record_count": 1,
        "models": {
            "model-a": {"records": [{"record_id": "rid-a", "cohort": "cohort-a", "score": 0.5}]}
        },
    }
    envelope = score_cache.encrypt_score_cache(
        legacy_v4, key=key, dataset_revision="synthetic-revision", code_sha="synthetic-code-sha"
    )

    with pytest.raises(ValueError, match="cache v4 record is missing doc_id"):
        score_cache.decrypt_score_cache(envelope, key=key)


def test_score_cache_join_rejects_incomplete_label_coverage() -> None:
    kwargs = {
        "protocols": {},
        "manifest_sha256": "m" * 64,
        "source_run_id": "synthetic-run",
        "source_code_sha": "synthetic-code-sha",
        "calibration_v2": None,
    }
    rows = [
        {"record_id": "rid-a", "cohort": "cohort-a", "score": 0.25},
        {"record_id": "rid-b", "cohort": "cohort-a", "score": 0.75},
    ]
    scores = score_cache.build_score_cache({"model-a": rows}, **kwargs)
    labels = score_cache.build_gold_label_cache(
        [
            {"record_id": "rid-a", "cohort": "cohort-a", "gold": "SUPPORTED"},
            {"record_id": "rid-b", "cohort": "cohort-a", "gold": "NOT_SUPPORTED"},
        ],
        manifest_sha256="m" * 64,
        source_run_id="synthetic-run",
    )
    labels["records"].pop()

    with pytest.raises(ValueError, match="gold-label cache record count mismatch"):
        score_cache.join_scores_with_gold(scores, labels)


def test_score_cache_join_rejects_wrong_split_and_manifest() -> None:
    kwargs = {
        "protocols": {},
        "manifest_sha256": "m" * 64,
        "source_run_id": "synthetic-run",
        "source_code_sha": "synthetic-code-sha",
        "calibration_v2": None,
    }
    scores = score_cache.build_score_cache(
        {"model-a": [{"record_id": "rid-a", "cohort": "cohort-a", "score": 0.5}]},
        **kwargs,
    )
    labels = score_cache.build_gold_label_cache(
        [{"record_id": "rid-a", "cohort": "cohort-a", "gold": "SUPPORTED"}],
        manifest_sha256="m" * 64,
        source_run_id="synthetic-run",
    )

    with pytest.raises(ValueError, match="only DEV"):
        score_cache.join_scores_with_gold(dict(scores, split="test"), labels)
    with pytest.raises(ValueError, match="manifest_sha256 mismatch"):
        score_cache.join_scores_with_gold(
            scores, dict(labels, manifest_sha256="different-manifest")
        )


def test_gold_label_cache_rejects_invalid_values_and_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="gold must be"):
        score_cache.build_gold_label_cache(
            [{"record_id": "rid-a", "cohort": "cohort-a", "gold": "UNKNOWN"}],
            manifest_sha256="m" * 64,
            source_run_id="synthetic-run",
        )

    duplicate = {"record_id": "rid-a", "cohort": "cohort-a", "gold": "SUPPORTED"}
    with pytest.raises(ValueError, match="duplicate record_id"):
        score_cache.build_gold_label_cache(
            [duplicate, duplicate],
            manifest_sha256="m" * 64,
            source_run_id="synthetic-run",
        )


def test_score_cache_decryption_rejects_wrong_envelope_role() -> None:
    kwargs = {
        "protocols": {},
        "manifest_sha256": "m" * 64,
        "source_run_id": "synthetic-run",
        "source_code_sha": "synthetic-code-sha",
        "calibration_v2": None,
    }
    cache = score_cache.build_score_cache(
        {"model-a": [{"record_id": "rid-a", "cohort": "cohort-a", "score": 0.5}]},
        **kwargs,
    )
    key = bytes(range(32))
    envelope = score_cache.encrypt_score_cache(
        cache, key=key, dataset_revision="synthetic-revision", code_sha="synthetic-code-sha"
    )
    wrong_role = {
        **envelope,
        "metadata": {**envelope["metadata"], "shard_id": "dev-gold-labels"},
    }

    with pytest.raises(ValueError, match="not a DEV score cache"):
        score_cache.decrypt_score_cache(wrong_role, key=key)
