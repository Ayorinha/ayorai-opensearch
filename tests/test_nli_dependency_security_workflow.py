from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "nli-dependency-smoke.yml"
PYPROJECT = ROOT / "pyproject.toml"
REQUIREMENTS = ROOT / "requirements-benchmark-pilot.txt"


def test_nli_smoke_audits_the_fully_installed_optional_environment() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    requirements = REQUIREMENTS.read_text(encoding="utf-8")

    cpu_torch = workflow.index(
        'python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.14.0"'
    )
    install_extras = workflow.index(
        'python -m pip install --index-url https://pypi.org/simple -e ".[dev,nli]"'
    )
    install_pilot = workflow.index(
        "python -m pip install --index-url "
        "https://pypi.org/simple -r requirements-benchmark-pilot.txt"
    )
    pip_check = workflow.index("pip check", install_pilot)
    uninstall_local = workflow.index(
        "- name: Remove the local editable project before auditing third-party dependencies",
        pip_check,
    )
    osv_audit = workflow.index(
        "- name: Audit optional dependencies against OSV, including CPU PyTorch",
        uninstall_local,
    )
    osv_command = workflow.index("run: pip-audit --strict --vulnerability-service osv", osv_audit)
    remove_torch = workflow.index(
        "- name: Remove CPU PyTorch for the PyPI-native dependency audit",
        osv_command,
    )
    pypi_audit = workflow.index(
        "- name: Audit PyPI dependencies with strict collection",
        remove_torch,
    )
    pypi_command = workflow.index("run: pip-audit --strict", pypi_audit)
    restore_torch = workflow.index(
        "- name: Restore the pinned CPU PyTorch wheel",
        pypi_command,
    )
    restore_torch_command = workflow.index(
        'run: python -m pip install --index-url '
        'https://download.pytorch.org/whl/cpu "torch==2.14.0"',
        restore_torch,
    )
    restore_local = workflow.index(
        "- name: Restore the local project without changing resolved dependencies",
        restore_torch_command,
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
        < osv_audit
        < osv_command
        < remove_torch
        < pypi_audit
        < pypi_command
        < restore_torch
        < restore_torch_command
        < restore_local
        < restore_command
        < verify_versions
    )
    assert "assert torch.version.cuda is None" in workflow
    assert '"pip==26.3" "setuptools==84.2.1"' in workflow
    assert "accelerate" not in requirements
    assert '"torch>=2.14,<3"' in pyproject
    assert '"pip-audit>=2.9,<3"' in pyproject
    assert "--skip-editable" not in workflow
    assert "pip-audit --strict --vulnerability-service osv" in workflow
    assert "pip-audit --strict" in workflow
    assert "python -m pip uninstall -y torch" in workflow
