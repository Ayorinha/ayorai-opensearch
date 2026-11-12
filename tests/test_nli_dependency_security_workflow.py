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
    install_extras = workflow.index(
        'python -m pip install --index-url https://pypi.org/simple -e ".[dev,nli]"'
    )
    install_pilot = workflow.index(
        "python -m pip install --index-url https://pypi.org/simple -r requirements-benchmark-pilot.txt"
    )
    pip_check = workflow.index("pip check", install_pilot)
    uninstall_local = workflow.index(
        "- name: Remove the local editable project before auditing third-party dependencies",
        pip_check,
    )
    audit_step = workflow.index(
        "- name: Audit the complete optional NLI and benchmark dependency environment",
        uninstall_local,
    )
    audit_command = workflow.index("run: pip-audit --strict", audit_step)
    restore_local = workflow.index(
        "- name: Restore the local project without changing resolved dependencies",
        audit_command,
    )
    restore_command = workflow.index("run: python -m pip install --no-deps -e .", restore_local)
    verify_versions = workflow.index(
        "- name: Verify installed dependency versions",
        restore_command,
    )

    assert (
        cpu_torch
        < install_extras
        < install_pilot
        < pip_check
        < uninstall_local
        < audit_step
        < audit_command
        < restore_local
        < restore_command
        < verify_versions
    )
    assert "assert torch.version.cuda is None" in workflow
    assert '"pip-audit>=2.9,<3"' in pyproject
    assert "--skip-editable" not in workflow
