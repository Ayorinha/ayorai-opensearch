"""T-1/T-2: each Phase 1b DEV workflow may reach only the secrets and runs it needs.

A text search for one secret name misses indirect exposure (``toJSON(secrets)``,
``secrets[format(...)]``, ``secrets: inherit``). These tests parse every ``${{ }}``
expression instead and accept only plain ``secrets.NAME`` references from an
allow-list per workflow. They also restrict which workflows may download artifacts
from another run.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(".github/workflows")
ARTIFACT_KEY = "PHASE1B_ARTIFACT_ENCRYPTION_KEY"
GOLD_KEY = "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY"
ALLOWED_SECRETS = {
    "phase1b-dev-full.yml": {ARTIFACT_KEY, GOLD_KEY, "HF_TOKEN"},
    # The minimal run computes no quality metric: it must never reach the gold key.
    "phase1b-dev-minimal.yml": {ARTIFACT_KEY, "HF_TOKEN"},
    "phase1b-dev-full-reaggregate.yml": {ARTIFACT_KEY, GOLD_KEY},
    "phase1b-dev-cache-experiment.yml": {ARTIFACT_KEY, GOLD_KEY},
}
# Only the recovery workflows read another run's artifacts, and only the run their
# provenance step verifies.
CROSS_RUN_INPUT = {
    "phase1b-dev-full-reaggregate.yml": "${{ inputs.source_run_id }}",
    "phase1b-dev-cache-experiment.yml": "${{ inputs.cache_run_id }}",
}
EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.DOTALL)
PLAIN_SECRET = re.compile(r"^\s*secrets\.([A-Z][A-Z0-9_]*)\s*$")


def _secret_names(text: str) -> set[str]:
    names = set()
    for expression in EXPRESSION.findall(text):
        if "secrets" not in expression:
            continue
        match = PLAIN_SECRET.fullmatch(expression)
        assert match, f"indirect secret expression: ${{{{{expression}}}}}"
        names.add(match.group(1))
    return names


def _steps(workflow: dict) -> list[dict]:
    return [step for job in workflow["jobs"].values() for step in job.get("steps", [])]


@pytest.mark.parametrize("name", sorted(ALLOWED_SECRETS))
def test_workflow_reaches_only_its_allowed_secrets(name: str) -> None:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    assert "secrets: inherit" not in text
    names = _secret_names(text)
    assert names <= ALLOWED_SECRETS[name], names - ALLOWED_SECRETS[name]
    # The artifact key is always needed; the check above is not vacuous.
    assert ARTIFACT_KEY in names


@pytest.mark.parametrize(
    "expression",
    [
        "${{ toJSON(secrets) }}",
        "${{ secrets[format('PHASE1B_GOLD_{0}', 'LABEL_ENCRYPTION_KEY')] }}",
        "${{ secrets['PHASE1B_GOLD_LABEL_ENCRYPTION_KEY'] }}",
        "${{ github.event_name == 'x' && secrets.OTHER || '' }}",
    ],
)
def test_indirect_secret_expressions_are_rejected(expression: str) -> None:
    with pytest.raises(AssertionError, match="indirect secret expression"):
        _secret_names(f"env:\n  X: {expression}\n")


def test_gold_key_is_absent_from_the_minimal_workflow_in_any_form() -> None:
    text = (WORKFLOWS / "phase1b-dev-minimal.yml").read_text(encoding="utf-8")
    assert GOLD_KEY not in _secret_names(text)
    assert "GOLD_LABEL" not in text.upper().replace("DISCARD-GOLD-LABELS", "")


@pytest.mark.parametrize("name", sorted(ALLOWED_SECRETS))
def test_cross_run_artifact_downloads_only_in_recovery_workflows(name: str) -> None:
    workflow = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    downloads = [
        step
        for step in _steps(workflow)
        if "actions/download-artifact" in str(step.get("uses", ""))
    ]
    run_ids = {str((step.get("with") or {}).get("run-id")) for step in downloads}
    run_ids.discard("None")
    if name in CROSS_RUN_INPUT:
        assert run_ids == {CROSS_RUN_INPUT[name]}
    else:
        assert run_ids == set(), f"{name} downloads artifacts from another run"
