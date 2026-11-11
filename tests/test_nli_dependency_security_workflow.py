from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "nli-dependency-smoke.yml"
PYPROJECT = ROOT / "pyproject.toml"


def test_nli_smoke_audits_the_fully_installed_optional_environment() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    pyproject = PYPROJECT.read_text(encoding="utf-8")

    cpu_torch = workflow.index(
        'python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.7.1"'
    )
    install_extras = workflow.index('python -m pip install --index-url https://pypi.org/simple -e ".[dev,nli]"')
    install_pilot = workflow.index("python -m pip install --index-url https://pypi.org/simple -r requirements-benchmark-pilot.txt")
    pip_check = workflow.index("pip check", install_pilot)
    audit_step = workflow.index(
        "- name: Audit the complete optional NLI and benchmark dependency environment",
        pip_check,
    )
    audit_command = workflow.index("run: pip-audit --strict", audit_step)
    verify_versions = workflow.index(
        "- name: Verify installed dependency versions",
        audit_command,
    )

    assert cpu_torch < install_extras < install_pilot < pip_check < audit_step < audit_command < verify_versions
    assert "assert torch.version.cuda is None" in workflow
    assert '"pip-audit>=2.9,<3"' in pyproject
