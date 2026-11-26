"""In-process tests of the Phase 1b CLIs that run inside the key-holding jobs (S-08).

The subprocess CLI tests elsewhere prove the scripts run; these call ``main()`` in the
test process so that the argument handling, key checks and refusal paths are measured.
Synthetic data only.
"""

from __future__ import annotations

import base64
import json
import secrets
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts.benchmarks.phase1b import common, inference_artifact, manifest_artifact
from scripts.benchmarks.phase1b import prepare_dev_artifacts as prepare

PIN = json.loads(common.DEV_PIN_PATH.read_text(encoding="utf-8"))
CODE_SHA = "e" * 40


def _key() -> str:
    return base64.b64encode(secrets.token_bytes(32)).decode()


def _rows() -> list[dict[str, str]]:
    return [
        {"doc": f"d{i}", "claim": f"c{i}", "dataset": "A" if i % 2 else "B", "label": str(i % 2)}
        for i in range(4)
    ]


def _manifest(dataset_sha256: str) -> dict[str, Any]:
    ids = sorted(common.stable_record_id(row) for row in _rows())
    manifest: dict[str, Any] = {
        "split": "dev",
        "schema_version": common.MANIFEST_SCHEMA_VERSION,
        "record_id_method": common.RECORD_ID_METHOD,
        "dataset_revision": PIN["revision"],
        "dataset_sha256": dataset_sha256,
        "code_sha": CODE_SHA,
        "sample_count": len(ids),
        "shards": [
            {
                "shard_id": "dev-0000",
                "count": len(ids),
                "record_ids": ids,
                "record_ids_sha256": common.sha256_bytes(common.canonical_json(ids)),
            }
        ],
    }
    manifest["manifest_sha256"] = common.sha256_bytes(common.canonical_json(manifest))
    return manifest


def _run(monkeypatch: pytest.MonkeyPatch, module: Any, *argv: str) -> None:
    monkeypatch.setattr(sys, "argv", [module.__name__, *argv])
    module.main()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    dataset = tmp_path / "dev.jsonl"
    dataset.write_text("".join(json.dumps(row) + "\n" for row in _rows()), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest(common.sha256_file(dataset))), encoding="utf-8")
    monkeypatch.setenv("PHASE1B_ARTIFACT_ENCRYPTION_KEY", _key())
    monkeypatch.setenv("PHASE1B_GOLD_LABEL_ENCRYPTION_KEY", _key())
    return {"dir": tmp_path, "dataset": dataset, "manifest": manifest}


def _prepare_args(ws: dict[str, Any]) -> list[str]:
    directory = ws["dir"]
    return [
        "--dataset-path",
        str(ws["dataset"]),
        "--manifest",
        str(ws["manifest"]),
        "--inference-output",
        str(directory / "inference.jsonl"),
        "--gold-label-cache-output",
        str(directory / "gold.json"),
        "--run-id",
        "101",
        "--code-sha",
        CODE_SHA,
    ]


def test_prepare_then_inference_round_trip_through_the_clis(
    workspace: dict[str, Any], monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    directory = workspace["dir"]
    _run(monkeypatch, prepare, *_prepare_args(workspace))
    summary = json.loads(capsys.readouterr().out)
    assert summary["labels_in_inference_input"] is False
    assert summary["record_count"] == 4
    updated = json.loads(workspace["manifest"].read_text(encoding="utf-8"))
    assert updated["inference_dataset_sha256"] == summary["inference_dataset_sha256"]

    common_args = ["--manifest", str(workspace["manifest"]), "--run-id", "101"]
    _run(
        monkeypatch,
        inference_artifact,
        "encrypt",
        "--input",
        str(directory / "inference.jsonl"),
        "--output",
        str(directory / "inference.aesgcm"),
        *common_args,
        "--code-sha",
        CODE_SHA,
    )
    _run(
        monkeypatch,
        inference_artifact,
        "decrypt",
        "--input",
        str(directory / "inference.aesgcm"),
        "--output",
        str(directory / "inference.out.jsonl"),
        *common_args,
        "--code-sha",
        CODE_SHA,
    )
    assert (directory / "inference.out.jsonl").read_bytes() == (
        directory / "inference.jsonl"
    ).read_bytes()
    with pytest.raises(ValueError, match="code SHA"):
        _run(
            monkeypatch,
            inference_artifact,
            "decrypt",
            "--input",
            str(directory / "inference.aesgcm"),
            "--output",
            str(directory / "x.jsonl"),
            *common_args,
            "--code-sha",
            "f" * 40,
        )


def test_prepare_refuses_equal_keys(workspace: dict[str, Any], monkeypatch: Any) -> None:
    key = _key()
    monkeypatch.setenv("PHASE1B_ARTIFACT_ENCRYPTION_KEY", key)
    monkeypatch.setenv("PHASE1B_GOLD_LABEL_ENCRYPTION_KEY", key)
    with pytest.raises(ValueError, match="distinct"):
        _run(monkeypatch, prepare, *_prepare_args(workspace))
    assert not (workspace["dir"] / "inference.jsonl").exists()


def test_prepare_requires_the_gold_key(workspace: dict[str, Any], monkeypatch: Any) -> None:
    monkeypatch.delenv("PHASE1B_GOLD_LABEL_ENCRYPTION_KEY")
    with pytest.raises(RuntimeError, match="PHASE1B_GOLD_LABEL_ENCRYPTION_KEY"):
        _run(monkeypatch, prepare, *_prepare_args(workspace))


def test_prepare_refuses_a_dataset_other_than_the_manifest(
    workspace: dict[str, Any], monkeypatch: Any
) -> None:
    workspace["dataset"].write_text(
        workspace["dataset"].read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="dataset SHA-256"):
        _run(monkeypatch, prepare, *_prepare_args(workspace))
    assert not (workspace["dir"] / "gold.json").exists()


def test_manifest_cli_round_trip_and_wrong_run(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("PHASE1B_ARTIFACT_ENCRYPTION_KEY", _key())
    manifest = _manifest(PIN["sha256"])
    (tmp_path / "m.json").write_text(json.dumps(manifest), encoding="utf-8")
    base = ["--code-sha", CODE_SHA]
    _run(
        monkeypatch,
        manifest_artifact,
        "encrypt",
        "--input",
        str(tmp_path / "m.json"),
        "--output",
        str(tmp_path / "m.aesgcm"),
        "--run-id",
        "101",
        *base,
    )
    assert "record_ids" not in (tmp_path / "m.aesgcm").read_text(encoding="utf-8")
    _run(
        monkeypatch,
        manifest_artifact,
        "decrypt",
        "--input",
        str(tmp_path / "m.aesgcm"),
        "--output",
        str(tmp_path / "out.json"),
        "--run-id",
        "101",
        *base,
    )
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8")) == manifest
    with pytest.raises(ValueError, match="metadata"):
        _run(
            monkeypatch,
            manifest_artifact,
            "decrypt",
            "--input",
            str(tmp_path / "m.aesgcm"),
            "--output",
            str(tmp_path / "x.json"),
            "--run-id",
            "102",
            *base,
        )
    assert not (tmp_path / "x.json").exists()


def test_clis_refuse_to_start_without_the_artifact_key(
    workspace: dict[str, Any], monkeypatch: Any
) -> None:
    monkeypatch.delenv("PHASE1B_ARTIFACT_ENCRYPTION_KEY")
    with pytest.raises(RuntimeError, match="PHASE1B_ARTIFACT_ENCRYPTION_KEY"):
        _run(
            monkeypatch,
            manifest_artifact,
            "encrypt",
            "--input",
            str(workspace["manifest"]),
            "--output",
            str(workspace["dir"] / "m.aesgcm"),
            "--run-id",
            "101",
            "--code-sha",
            CODE_SHA,
        )
    assert not (workspace["dir"] / "m.aesgcm").exists()
