"""In-process coverage for Phase 1b aggregation and score-cache CLIs.

All fixtures are synthetic. These tests exercise the same entry points used by
the workflows while keeping the Python code under test in the pytest process,
so coverage.py can measure the critical CLI paths.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

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
    manifest, encrypted_dir, environment, rows_by_id, gold_cache = _write_synthetic_inputs(
        tmp_path
    )
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
    score_envelope_text = score_cache_output.read_text(encoding="utf-8")
    score_envelope = json.loads(score_envelope_text)
    assert aggregate_summary["status"] == "complete"
    assert aggregate_report["quality_metrics"] == "calibration_v2_aggregate_only"
    assert score_envelope["metadata"]["shard_id"] == score_cache.SCORE_CACHE_SHARD_ID
    assert "gold" not in score_envelope_text.lower()
    assert not any(record_id in score_envelope_text for record_id in rows_by_id)

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
