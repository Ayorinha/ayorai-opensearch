""""Security contract tests for the stacked P1 confirmation workflow."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/phase1b-dev-cache-experiment.yml")
APPROVAL_ENVIRONMENT = "international-benchmark-maintainer-approval"


def test_p1_workflow_separates_read_only_and_write_jobs() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"experiment-read-only", "p1-confirmation"}

    read_only = jobs["experiment-read-only"]
    assert read_only["if"] == "inputs.experiment != 'e3-confirm-dev-b'"
    assert read_only["permissions"] == {"contents": "read", "actions": "read"}
    assert read_only["environment"] == APPROVAL_ENVIRONMENT
    assert any(step.get("with", {}).get("persist-credentials") is False for step in read_only["steps"])

    p1 = jobs["p1-confirmation"]
    assert p1["if"] == "inputs.experiment == 'e3-confirm-dev-b'"
    assert p1["permissions"] == {"contents": "write", "actions": "read"}
    assert p1["environment"] == APPROVAL_ENVIRONMENT
    assert any(step.get("with", {}).get("persist-credentials") is False for step in p1["steps"])


def test_both_cache_jobs_reject_non_main_dispatch_before_checkout_or_secrets() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    for job_name, decrypt_name in (
        ("experiment-read-only", "Decrypt cache and run read-only experiment"),
        ("p1-confirmation", "Decrypt cache and run P1 with a one-shot lock"),
    ):
        steps = jobs[job_name]["steps"]
        guard = steps[0]
        assert guard["name"] == "Require canonical protected-main dispatch before checkout"
        assert guard["shell"] == "bash"
        assert '[[ "$GITHUB_REPOSITORY" == "Ayorinha/ayorai-opensearch" ]]' in guard["run"]
        assert '[[ "$GITHUB_REF" == "refs/heads/main" ]]' in guard["run"]
        assert '[[ "$GITHUB_EVENT_NAME" == "workflow_dispatch" ]]' in guard["run"]
        assert '[[ "$GITHUB_RUN_ID" =~ ^[0-9]+$ ]]' in guard["run"]
        assert '[[ "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]' in guard["run"]
        assert "env" not in guard
        assert steps[1]["uses"].startswith("actions/checkout@")
        decrypt = next(step for step in steps if step.get("name") == decrypt_name)
        assert steps.index(decrypt) > 1
        assert "PHASE1B_ARTIFACT_ENCRYPTION_KEY" in decrypt["env"]
        secret_steps = [
            index
            for index, step in enumerate(steps)
            if "PHASE1B_ARTIFACT_ENCRYPTION_KEY" in step.get("env", {})
        ]
        assert secret_steps
        assert min(secret_steps) > 1


def test_p1_global_single_flight_and_non_p1_ref_scoping() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    concurrency = workflow["concurrency"]
    group = concurrency["group"]
    assert "inputs.experiment == 'e3-confirm-dev-b'" in group
    assert "p1-dev-b-confirmation-single-flight" in group
    assert "github.ref" in group
    assert concurrency["cancel-in-progress"] is False


def test_p1_is_manual_approval_gated_and_does_not_run_inference() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    p1 = workflow["jobs"]["p1-confirmation"]
    assert p1["environment"] == APPROVAL_ENVIRONMENT
    assert "run_shard.py" not in text
    assert "fetch_dev.py" not in text
    assert "--split test" not in text

    lock_step = next(
        step
        for step in p1["steps"]
        if step.get("name") == "Decrypt cache and run P1 with a one-shot lock"
    )
    assert "GH_TOKEN" in lock_step["env"]
    run = lock_step["run"]
    assert "unset GH_TOKEN" in run
    assert run.index("score_cache.py") < run.index("unset GH_TOKEN")
    assert run.index("unset GH_TOKEN") < run.index("python - <<'PY'")
