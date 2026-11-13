"""Write permissions must be granted per job, never to a whole workflow."""

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
FILES = sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))


@pytest.mark.parametrize("path", FILES, ids=lambda path: path.name)
def test_workflow_level_permissions_are_read_only(path: Path) -> None:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    permissions = workflow.get("permissions", {})
    assert permissions != "write-all", path.name
    if isinstance(permissions, dict):
        writes = sorted(scope for scope, level in permissions.items() if level == "write")
        assert writes == [], f"{path.name}: move {writes} to the job that needs them"


def test_codeql_upload_permission_is_scoped_to_the_analysis_job() -> None:
    workflow = yaml.safe_load((WORKFLOWS / "codeql.yml").read_text(encoding="utf-8"))
    assert workflow["permissions"] == {}
    assert workflow["jobs"]["analyze"]["permissions"] == {
        "contents": "read",
        "security-events": "write",
    }
