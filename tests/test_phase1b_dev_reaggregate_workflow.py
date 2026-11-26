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
    assert "-r requirements-phase1b-protected.txt" in text
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
    # Re-uploaded caches inherit what is left of the source run's 30-day window.
    assert all(
        step["with"]["retention-days"] == "${{ steps.source.outputs.cache_retention_days }}"
        for step in cache_uploads.values()
    )


def _step(name: str) -> dict:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    return next(step for step in workflow["jobs"]["aggregate"]["steps"] if step.get("name") == name)


def test_reaggregate_requires_the_source_commit_on_main_of_this_repository() -> None:
    step = _step("Verify source run provenance")
    script = step["run"]
    assert step["id"] == "source"
    assert '["head_repository"]["full_name"]' in script
    assert 'test "$SOURCE_REPOSITORY" = "$GITHUB_REPOSITORY"' in script
    assert "compare/${SOURCE_SHA}...main" in script
    assert '"$status" == "identical" || "$status" == "ahead"' in script


def test_reaggregate_cache_retention_never_exceeds_the_source_window() -> None:
    script = _step("Verify source run provenance")["run"]
    assert 'run["created_at"]' in script
    assert "remaining = 30 - math.ceil(age_days)" in script
    assert "assert remaining >= 1" in script
    assert "cache_retention_days={remaining}" in script


def test_full_workflow_aggregate_installs_numpy() -> None:
    workflow = yaml.safe_load(FULL_WORKFLOW_PATH.read_text(encoding="utf-8"))
    install = next(
        step["run"]
        for step in workflow["jobs"]["aggregate"]["steps"]
        if step.get("name") == "Install pinned dependencies"
    )
    assert "--require-hashes" in install
    assert "-r requirements-phase1b-protected.txt" in install
    lock = Path("requirements-phase1b-protected.txt").read_text(encoding="utf-8")
    assert "numpy==2.2.6 \\" in lock
