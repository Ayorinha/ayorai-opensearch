"""Static guardrails for the A1 score cache: producers and the experiment workflow."""

from __future__ import annotations

from pathlib import Path

import yaml

EXPERIMENT = Path(".github/workflows/phase1b-dev-cache-experiment.yml")
PRODUCERS = (
    Path(".github/workflows/phase1b-dev-full.yml"),
    Path(".github/workflows/phase1b-dev-full-reaggregate.yml"),
)
APPROVAL_ENVIRONMENT = "international-benchmark-maintainer-approval"


def test_experiment_workflow_is_manual_gated_and_inference_free() -> None:
    text = EXPERIMENT.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}

    jobs = workflow["jobs"]
    if set(jobs) == {"experiment"}:
        # Base implementation before the stacked P1 workflow split.
        assert jobs["experiment"]["environment"] == APPROVAL_ENVIRONMENT
        assert jobs["experiment"].get("permissions", workflow["permissions"]) == {
            "contents": "read",
            "actions": "read",
        }
    elif set(jobs) == {"experiment-read-only", "p1-confirmation"}:
        # Stacked P1 implementation: ordinary experiments stay read-only.
        read_only = jobs["experiment-read-only"]
        assert read_only["if"] == "inputs.experiment != 'e3-confirm-dev-b'"
        assert read_only["permissions"] == {"contents": "read", "actions": "read"}
        assert read_only["environment"] == APPROVAL_ENVIRONMENT

        p1 = jobs["p1-confirmation"]
        assert p1["if"] == "inputs.experiment == 'e3-confirm-dev-b'"
        assert p1["permissions"] == {"contents": "write", "actions": "read"}
        assert p1["environment"] == APPROVAL_ENVIRONMENT
        assert workflow["concurrency"]["cancel-in-progress"] is False
        assert any(step.get("with", {}).get("persist-credentials") is False for step in p1["steps"])
    else:
        raise AssertionError(f"unexpected experiment workflow jobs: {sorted(jobs)}")

    for forbidden in ("run_shard.py", "fetch_dev.py", "--split test"):
        assert forbidden not in text
    assert "run-id: ${{ inputs.cache_run_id }}" in text
    assert "replay_matches_source" in text


def test_producers_upload_only_the_encrypted_cache() -> None:
    for path in PRODUCERS:
        text = path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(text)
        steps = next(iter(workflow["jobs"][job] for job in workflow["jobs"] if "aggregate" in job))[
            "steps"
        ]
        uploads = [step for step in steps if "upload-artifact" in str(step.get("uses", ""))]
        cache_uploads = [
            step for step in uploads if step["with"]["name"] == "phase1b-dev-score-cache"
        ]
        assert len(cache_uploads) == 1, path
        assert cache_uploads[0]["with"]["path"].endswith("phase1b-dev-score-cache.json")
        assert "--score-cache-output" in text
