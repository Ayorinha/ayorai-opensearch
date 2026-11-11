from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
SECURITY_WORKFLOW = ROOT / ".github" / "workflows" / "security.yml"
DEPENDENCY_REVIEW_WORKFLOW = ROOT / ".github" / "workflows" / "dependency-review.yml"


def test_python_dependency_audit_fails_on_incomplete_collection() -> None:
    workflow = yaml.safe_load(SECURITY_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["security"]["steps"]

    assert any(step.get("run") == "pip-audit --strict" for step in steps)


def test_high_severity_dependency_review_is_a_required_gate() -> None:
    workflow = yaml.safe_load(DEPENDENCY_REVIEW_WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"]["dependency-review"]
    review_step = next(step for step in job["steps"] if step.get("name") == "Review dependency changes")

    assert job.get("continue-on-error", False) is False
    assert review_step["with"]["fail-on-severity"] == "high"
    assert review_step["with"]["warn-only"] is False
    assert re.search(r"@[0-9a-f]{40}(?:\\s|$)", review_step["uses"])
    assert workflow["permissions"] == {"contents": "read"}
