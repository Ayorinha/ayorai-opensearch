"""Checkout credentials are not persisted except where a workflow pushes with git."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
GIT_PUSH_EXCEPTION = "source-capture.yml"


def test_checkout_does_not_persist_credentials_unless_git_push_requires_them() -> None:
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

                if path.name == GIT_PUSH_EXCEPTION:
                    # This workflow commits and pushes its generated source-capture record.
                    assert persisted is not False
                else:
                    assert persisted is False, f"{path.name}: checkout must not persist credentials"

    assert GIT_PUSH_EXCEPTION in checked_out_workflows
    source_capture = (WORKFLOWS / GIT_PUSH_EXCEPTION).read_text(encoding="utf-8")
    assert 'git push origin "HEAD:${GITHUB_REF_NAME}"' in source_capture
