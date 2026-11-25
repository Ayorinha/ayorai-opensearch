"""Static guardrails for the maintainer-gated full DEV workflow."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW_PATH = Path(".github/workflows/phase1b-dev-full.yml")
MINIMAL_PATH = Path(".github/workflows/phase1b-dev-minimal.yml")
APPROVAL_ENVIRONMENT = "international-benchmark-maintainer-approval"


def test_full_dev_workflow_is_manual_and_environment_gated() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.load(workflow_text, Loader=yaml.BaseLoader)

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    confirmation = workflow["on"]["workflow_dispatch"]["inputs"]["confirmation"]
    assert confirmation["required"] == "true"
    assert confirmation["options"] == ["full-dev-calibration-v2"]
    assert "github.ref == 'refs/heads/main'" in workflow["jobs"]["plan"]["if"]
    downloads = [
        step
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "download-artifact" in str(step.get("uses", ""))
    ]
    assert downloads and all(
        step["with"].get("github-token") == "${{ github.token }}" for step in downloads
    )
    assert set(workflow["jobs"]) == {"plan", "shard", "aggregate"}
    assert all(job["environment"] == APPROVAL_ENVIRONMENT for job in workflow["jobs"].values())
    shard = workflow["jobs"]["shard"]
    shard_text = str(shard)
    assert "fetch_dev.py" not in shard_text
    assert "HF_TOKEN" not in shard_text
    assert "phase1b-dev-inference-data-encrypted" in shard_text
    assert "phase1b-dev-full-manifest-encrypted" in shard_text
    assert "manifest_artifact.py decrypt" in shard_text
    assert "github-token: ${{ github.token }}" in workflow_text
    assert "inference_artifact.py decrypt" in shard_text
    assert int(shard["timeout-minutes"]) >= 180
    assert shard["strategy"]["fail-fast"] == "false"
    assert int(shard["strategy"]["max-parallel"]) == 20


def test_full_dev_workflow_uses_full_dev_only_and_calibration_v2() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "--calibration-v2" in workflow_text
    assert "--shard-size 1000" in workflow_text
    assert "--seed 20261106" in workflow_text
    assert "--sample-size" not in workflow_text
    assert "--max-shards" not in workflow_text
    assert "--minimal" not in workflow_text
    assert "split: test" not in workflow_text.lower()
    assert "--split test" not in workflow_text.lower()
    assert '["mdeberta", "minicheck", "factcg"]' in workflow_text
    assert 'assert manifest["sample_count"] == 30420' in workflow_text
    assert 'assert report["calibration_v2"]["certification_model_count"] == 1' in workflow_text
    assert "phase1b-dev-full-encrypted-*" in workflow_text
    assert "prepare_dev_artifacts.py" in workflow_text
    assert "phase1b-dev-inference-data-encrypted" in workflow_text
    assert "phase1b-dev-full-manifest-encrypted" in workflow_text
    assert "manifest_artifact.py encrypt" in workflow_text
    assert "inference_artifact.py encrypt" in workflow_text
    assert "path: /tmp/phase1b-manifest.json.aesgcm" in workflow_text
    workflow = yaml.load(workflow_text, Loader=yaml.BaseLoader)
    manifest_uploads = [
        step
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "upload-artifact" in str(step.get("uses", ""))
        and step["with"].get("name") == "phase1b-dev-full-manifest-encrypted"
    ]
    assert len(manifest_uploads) == 1
    assert manifest_uploads[0]["with"]["path"] == "/tmp/phase1b-manifest.json.aesgcm"
    assert "path: /tmp/phase1b-dev-inference.jsonl.aesgcm" in workflow_text
    assert "phase1b-dev-gold-label-cache" in workflow_text
    assert "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY" in workflow_text
    assert "--gold-label-cache-input" in workflow_text
    assert "retention-days: 30" in workflow_text
    cache_uploads = {
        step["with"]["name"]: step
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "upload-artifact" in str(step.get("uses", ""))
        and step["with"].get("name")
        in {
            "phase1b-dev-gold-label-cache",
            "phase1b-dev-score-cache",
        }
    }
    assert set(cache_uploads) == {
        "phase1b-dev-gold-label-cache",
        "phase1b-dev-score-cache",
    }
    assert all(step["with"]["retention-days"] == "30" for step in cache_uploads.values())


def test_full_dev_workflow_reuses_exact_minimal_action_pins() -> None:
    full_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    minimal_text = MINIMAL_PATH.read_text(encoding="utf-8")
    minimal = yaml.load(minimal_text, Loader=yaml.BaseLoader)
    minimal_downloads = [
        step
        for job in minimal["jobs"].values()
        for step in job["steps"]
        if "download-artifact" in str(step.get("uses", ""))
    ]
    assert minimal_downloads and all(
        step["with"].get("github-token") == "${{ github.token }}" for step in minimal_downloads
    )
    action_prefixes = (
        "actions/checkout@",
        "actions/setup-python@",
        "actions/upload-artifact@",
        "actions/download-artifact@",
    )

    for action in action_prefixes:
        minimal_pins = {
            line.strip().split("#", 1)[0].strip()
            for line in minimal_text.splitlines()
            if line.strip().startswith("- uses: " + action)
        }
        full_pins = {
            line.strip().split("#", 1)[0].strip()
            for line in full_text.splitlines()
            if line.strip().startswith("- uses: " + action)
        }
        assert minimal_pins
        assert full_pins == minimal_pins


def test_every_secret_bearing_job_is_restricted_to_main() -> None:
    for path in (WORKFLOW_PATH, MINIMAL_PATH):
        workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        for job_name, job in workflow["jobs"].items():
            assert job["environment"] == APPROVAL_ENVIRONMENT
            assert "github.ref == 'refs/heads/main'" in job.get("if", ""), (
                f"{path}:{job_name} must be restricted to main"
            )


def test_full_dev_workflow_is_separate_from_minimal_workflow() -> None:
    assert WORKFLOW_PATH != MINIMAL_PATH
    assert WORKFLOW_PATH.is_file()
    assert MINIMAL_PATH.is_file()
    minimal = yaml.load(MINIMAL_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    minimal_text = MINIMAL_PATH.read_text(encoding="utf-8")
    assert "prepare_dev_artifacts.py" in minimal_text
    assert "phase1b-dev-minimal-inference-data-encrypted" in minimal_text
    assert "phase1b-dev-minimal-manifest-encrypted" in minimal_text
    assert "manifest_artifact.py encrypt" in minimal_text
    assert "manifest_artifact.py decrypt" in minimal_text
    assert "inference_artifact.py encrypt" in minimal_text
    assert "inference_artifact.py decrypt" in minimal_text
    assert "path: /tmp/phase1b-dev-inference.jsonl.aesgcm" in minimal_text
    assert "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY" in minimal_text
    assert "fetch_dev.py" not in str(minimal["jobs"]["shard"])
    assert "github.ref == 'refs/heads/main'" in minimal["jobs"]["plan"]["if"]


def test_dev_plan_jobs_clean_local_inputs_after_all_upload_attempts() -> None:
    sensitive_paths = (
        "$DEV_PARQUET",
        "$INFERENCE_DATA",
        "$INFERENCE_ENCRYPTED",
        "$MANIFEST_ENCRYPTED",
        "/tmp/phase1b-manifest.json",
        "/tmp/phase1b-matrix.json",
        "/tmp/phase1b-gold-labels",
    )

    for path in (WORKFLOW_PATH, MINIMAL_PATH):
        workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        steps = workflow["jobs"]["plan"]["steps"]
        cleanup = [
            (index, step)
            for index, step in enumerate(steps)
            if step.get("name") == "Remove local DEV inputs and encrypted intermediates"
        ]
        assert len(cleanup) == 1
        cleanup_index, cleanup_step = cleanup[0]
        assert cleanup_step["if"] == "${{ always() }}"
        assert all(item in cleanup_step["run"] for item in sensitive_paths)

        upload_indexes = [
            index
            for index, step in enumerate(steps)
            if "upload-artifact" in str(step.get("uses", ""))
        ]
        assert upload_indexes
        assert cleanup_index > max(upload_indexes)


def test_minimal_aggregate_removes_decrypted_inputs_on_failure() -> None:
    workflow = yaml.load(MINIMAL_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    aggregate_steps = workflow["jobs"]["aggregate"]["steps"]
    decrypt_step = next(
        step
        for step in aggregate_steps
        if step.get("name") == "Decrypt in protected job and publish operational aggregate only"
    )
    assert "trap 'rm -rf /tmp/phase1b-encrypted /tmp/phase1b-manifest' EXIT" in decrypt_step["run"]
