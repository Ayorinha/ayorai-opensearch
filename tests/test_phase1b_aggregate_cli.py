"""Run the aggregator exactly as the workflows do: by file path, in a clean subprocess.

Regression guard for the full DEV run where ``--calibration-v2`` failed with
``ModuleNotFoundError: No module named 'scripts'``. Synthetic data only.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from scripts.benchmarks.phase1b.build_manifest import build_manifest
from scripts.benchmarks.phase1b.calibration_v2.aggregate import COHORTS, MODEL_IDS
from scripts.benchmarks.phase1b.common import stable_record_id
from scripts.benchmarks.phase1b.encrypt_artifact import encrypt_bytes

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AGGREGATOR = REPOSITORY_ROOT / "scripts" / "benchmarks" / "phase1b" / "aggregate_dev.py"
CENTERS = {"mdeberta": (0.08, 0.92), "minicheck": (0.20, 0.80), "factcg": (0.12, 0.88)}


def _synthetic_rows() -> list[dict]:
    rows = []
    for cohort in COHORTS:
        for index in range(40):
            rows.append(
                {
                    "doc": f"SYNTHETIC document {cohort} {index}",
                    "claim": f"SYNTHETIC claim {cohort} {index}",
                    "label": index % 2,
                    "dataset": cohort,
                }
            )
    return rows


def test_aggregator_cli_by_path_computes_calibration_v2(tmp_path: Path) -> None:
    rows = _synthetic_rows()
    manifest = build_manifest(
        rows,
        dataset_sha256="c" * 64,
        dataset_revision="synthetic-revision",
        code_sha="synthetic-code-sha",
        shard_size=1000,
        seed=7,
    )
    rows_by_id = {stable_record_id(row): row for row in rows}
    key = bytes(range(32))
    rng = np.random.default_rng(20261107)
    encrypted_dir = tmp_path / "encrypted"
    encrypted_dir.mkdir()

    for model in MODEL_IDS:
        low, high = CENTERS[model]
        for shard in manifest["shards"]:
            records = []
            for record_id in shard["record_ids"]:
                row = rows_by_id[record_id]
                center = high if row["label"] else low
                records.append(
                    {
                        "record_id": record_id,
                        "cohort": row["dataset"],
                        "gold": "SUPPORTED" if row["label"] else "NOT_SUPPORTED",
                        "score": float(np.clip(center + rng.normal(0.0, 0.015), 0.0, 1.0)),
                    }
                )
            private = {
                "split": "dev",
                "shard_id": shard["shard_id"],
                "model_id": model,
                "model_revision": f"{model}-revision",
                "dataset_revision": "synthetic-revision",
                "dataset_sha256": "c" * 64,
                "code_sha": "synthetic-code-sha",
                "document_count": shard["count"],
                "block_count": shard["count"],
                "token_count_by_unit": {"synthetic_tokens": 0},
                "records": records,
            }
            metadata = {
                "run_id": "synthetic-run",
                "split": "dev",
                "model_revision": f"{model}-revision",
                "shard_id": shard["shard_id"],
                "dataset_revision": "synthetic-revision",
                "code_sha": "synthetic-code-sha",
            }
            envelope = encrypt_bytes(json.dumps(private).encode(), key=key, metadata=metadata)
            (encrypted_dir / f"{model}-{shard['shard_id']}.json").write_text(json.dumps(envelope))

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    output_path = tmp_path / "aggregate.json"
    env = {key_name: value for key_name, value in os.environ.items() if key_name != "PYTHONPATH"}
    env["PHASE1B_ARTIFACT_ENCRYPTION_KEY"] = base64.b64encode(key).decode()

    completed = subprocess.run(
        [
            sys.executable,
            str(AGGREGATOR),
            "--manifest",
            str(manifest_path),
            "--encrypted-dir",
            str(encrypted_dir),
            "--output",
            str(output_path),
            "--calibration-v2",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(output_path.read_text())
    serialized = json.dumps(report, sort_keys=True)
    assert report["complete"] is True
    assert report["quality_metrics"] == "calibration_v2_aggregate_only"
    assert report["calibration_v2"]["certification_model_count"] == 1
    assert "record_id" not in serialized
    assert "records" not in serialized
    assert not any(record_id in serialized for record_id in rows_by_id)
