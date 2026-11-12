"""Security contract tests for the stacked P1 confirmation workflow."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/phase1b-dev-cache-experiment.yml")
APPROVAL_ENVIRONMENT = "international-benchmark-maintainer-approval"


def test_all_p1_workflow_jobs_remain_read_only() -> None:
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
    ro_steps = read_only["steps"]
    assert any(step.get("with", {}).get("persist-credentials") is False for step in ro_steps)

    p1 = jobs["p1-confirmation"]
    assert p1["if"] == "inputs.experiment == 'e3-confirm-dev-b'"
    assert p1["permissions"] == {"contents": "read", "actions": "read"}
    assert p1["environment"] == APPROVAL_ENVIRONMENT
    assert all(job["permissions"].get("contents") != "write" for job in jobs.values())
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

    steps = p1["steps"]
    names = [step.get("name", step.get("uses", "")) for step in steps]

    def index(name: str) -> int:
        return names.index(name)

    download = next(
        i
        for i, step in enumerate(steps)
        if step.get("uses", "").startswith("actions/download-artifact@")
    )
    mint = next(
        i
        for i, step in enumerate(steps)
        if step.get("uses", "").startswith("actions/create-github-app-token@")
    )
    order = [
        index("Require P1 scientific authorization before cache download"),
        index("Require one-shot lock App configuration before cache download"),
        download,
        index("Validate decrypted cache before reserving P1"),
        mint,
        index("Reserve single-use P1 lock"),
        index("Decrypt cache and run P1 with a one-shot lock"),
    ]
    assert order == sorted(order)

    token = steps[mint]
    assert token["uses"].endswith("@64ab729a6294000f5aa4a4bc0b73d1f32bc45510 # v3.3.0") or (
        token["uses"] == "actions/create-github-app-token@64ab729a6294000f5aa4a4bc0b73d1f32bc45510"
    )
    assert token["with"]["permission-contents"] == "write"
    assert token["with"]["repositories"] == "ayorai-opensearch"
    assert set(token["with"]) == {
        "client-id",
        "private-key",
        "owner",
        "repositories",
        "permission-contents",
    }

    key = "PHASE1B_ARTIFACT_ENCRYPTION_KEY"
    for step in steps:
        env = step.get("env", {})
        text = str(step.get("run", ""))
        if "P1_LOCK_TOKEN" in env or "steps.p1-lock-token.outputs.token" in str(env):
            assert step["name"] == "Reserve single-use P1 lock"
            assert key not in env
        if key in env:
            assert "P1_LOCK_TOKEN" not in env and "P1_LOCK_TOKEN" not in text
            assert step["name"] in {
                "Validate decrypted cache before reserving P1",
                "Decrypt cache and run P1 with a one-shot lock",
            }
    reserve = steps[index("Reserve single-use P1 lock")]
    assert "--reserve-lock" in reserve["run"]
    assert reserve["env"] == {"P1_LOCK_TOKEN": "${{ steps.p1-lock-token.outputs.token }}"}

    run_step = steps[index("Decrypt cache and run P1 with a one-shot lock")]
    assert "GH_TOKEN" not in run_step["env"]
    assert "P1_LOCK_RESERVATION" in run_step["run"]
    assert "p1-lock-reservation.json" in str(steps[-1]["with"]["path"])
    assert "GITHUB_RUN_ATTEMPT" in steps[0]["run"]
    setup = next(s for s in steps if s.get("uses", "").startswith("actions/setup-python@"))
    assert "cache" not in setup.get("with", {})
