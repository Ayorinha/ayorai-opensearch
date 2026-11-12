from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SECURITY_WORKFLOW = ROOT / ".github" / "workflows" / "security.yml"
DEPENDENCY_REVIEW_WORKFLOW = ROOT / ".github" / "workflows" / "dependency-review.yml"


def test_python_dependency_audit_fails_on_incomplete_collection() -> None:
    workflow = yaml.safe_load(SECURITY_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["security"]["steps"]

    uninstall = next(
        index
        for index, step in enumerate(steps)
        if step.get("name")
        == "Remove the local editable project before auditing third-party dependencies"
    )
    osv_audit = next(
        index
        for index, step in enumerate(steps)
        if step.get("run") == "pip-audit --strict --vulnerability-service osv"
    )
    audit = next(
        index
        for index, step in enumerate(steps)
        if step.get("run") == "pip-audit --strict"
    )
    assert any(step.get("run") == 'pip install -e ".[dev]"' for step in steps)
    assert "python -m pip install --upgrade pip setuptools" in {step.get("run") for step in steps}
    assert uninstall < osv_audit < audit
    assert steps[uninstall]["run"] == "python -m pip uninstall -y ayorai-opensearch"


def test_high_severity_dependency_review_is_a_required_gate() -> None:
    workflow = yaml.safe_load(DEPENDENCY_REVIEW_WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"]["dependency-review"]
    review_step = next(
        step for step in job["steps"] if step.get("name") == "Review dependency changes"
    )

    assert job.get("continue-on-error", False) is False
    assert review_step["with"]["fail-on-severity"] == "high"
    assert review_step["with"]["warn-only"] is False
    pinned_ref = review_step["uses"].split("@", maxsplit=1)[1].split()[0]
    assert len(pinned_ref) == 40
    assert all(character in "0123456789abcdef" for character in pinned_ref)
    assert workflow["permissions"] == {"contents": "read"}
