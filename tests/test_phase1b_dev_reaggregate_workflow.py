"""Static guardrails for the maintainer-gated full DEV re-aggregation workflow."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW_PATH = Path(".github/workflows/phase1b-dev-full-reaggregate.yml")
FULL_WORKFLOW_PATH = Path(".github/workflows/phase1b-dev-full.yml")
APPROVAL_ENVIRONMENT = "international-benchmark-maintainer-approval"


def test_reaggregate_is_manual_gated_and_aggregate_only() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    assert set(workflow["jobs"]) == {"aggregate"}
    job = workflow["jobs"]["aggregate"]
    assert job["environment"] == APPROVAL_ENVIRONMENT
    assert "github.ref == 'refs/heads/main'" in job["if"]
    assert "run_shard.py" not in text
    assert "fetch_dev.py" not in text
    assert "--split test" not in text.lower()
    assert "--calibration-v2" in text
    assert "run-id: ${{ inputs.source_run_id }}" in text
    assert '".github/workflows/phase1b-dev-full.yml"' in text
    assert "numpy==2.2.6" in text
    assert "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY" in text
    assert "phase1b-dev-full-manifest-encrypted" in text
    assert "manifest_artifact.py decrypt" in text
    assert "phase1b-dev-gold-label-cache" in text
    assert "--gold-label-cache-input" in text
    workflow = yaml.safe_load(text)
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
    assert all(step["with"]["retention-days"] == 30 for step in cache_uploads.values())


def test_full_workflow_aggregate_installs_numpy() -> None:
    workflow = yaml.safe_load(FULL_WORKFLOW_PATH.read_text(encoding="utf-8"))
    install = next(
        step["run"]
        for step in workflow["jobs"]["aggregate"]["steps"]
        if step.get("name") == "Install pinned dependencies"
    )
    assert "numpy==2.2.6" in install
