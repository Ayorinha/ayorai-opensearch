"""All checkout credentials are scoped explicitly to the steps that need them."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_checkout_does_not_persist_credentials() -> None:
    checked_out_workflows: set[str] = set()

    for path in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(workflow, dict):
            continue

        for job in (workflow.get("jobs") or {}).values():
            for step in job.get("steps", []):
                uses = str(step.get("uses", ""))
                if not uses.startswith("actions/checkout@"):
                    continue

                checked_out_workflows.add(path.name)
                persisted = (step.get("with") or {}).get("persist-credentials")

                assert persisted is False, f"{path.name}: checkout must not persist credentials"

    assert "source-capture.yml" in checked_out_workflows
    source_capture = yaml.safe_load(
        (WORKFLOWS / "source-capture.yml").read_text(encoding="utf-8")
    )
    assert source_capture["permissions"]["contents"] == "write"
    push_step = next(
        step for step in source_capture["jobs"]["capture"]["steps"]
        if step.get("name") == "Commit captured artifacts to this branch"
    )
    assert push_step["env"]["GITHUB_TOKEN"] == "${{ github.token }}"
    assert "git -c http.extraheader=" in push_step["run"]
    assert 'push origin "HEAD:${GITHUB_REF_NAME}"' in push_step["run"]
