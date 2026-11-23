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
    assert set(workflow["jobs"]) == {"experiment"}
    assert workflow["jobs"]["experiment"]["environment"] == APPROVAL_ENVIRONMENT
    for forbidden in ("run_shard.py", "fetch_dev.py", "--split test"):
        assert forbidden not in text
    assert text.count("run-id: ${{ inputs.cache_run_id }}") == 2
    assert "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY" in text
    assert "--gold-labels" in text
    assert "replay_matches_source" in text


def test_producers_upload_only_the_encrypted_cache() -> None:
    for path in PRODUCERS:
        text = path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(text)
        steps = [step for job in workflow["jobs"].values() for step in job["steps"]]
        uploads = [step for step in steps if "upload-artifact" in str(step.get("uses", ""))]
        cache_uploads = {
            step["with"]["name"]: step
            for step in uploads
            if step["with"]["name"] in {"phase1b-dev-score-cache", "phase1b-dev-gold-label-cache"}
        }
        assert set(cache_uploads) == {"phase1b-dev-score-cache", "phase1b-dev-gold-label-cache"}, (
            path
        )
        assert cache_uploads["phase1b-dev-score-cache"]["with"]["path"].endswith(
            "phase1b-dev-score-cache.json"
        )
        assert cache_uploads["phase1b-dev-gold-label-cache"]["with"]["path"].endswith(
            "phase1b-dev-gold-label-cache.json"
        )
        assert "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY" in text
        assert "--score-cache-output" in text
        assert "--gold-label-cache-input" in text
        if path.name == "phase1b-dev-full.yml":
            assert "--gold-label-cache-output" in text
