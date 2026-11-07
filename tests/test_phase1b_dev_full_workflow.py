"""Static guardrails for the maintainer-gated full DEV workflow."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW_PATH = Path(".github/workflows/phase1b-dev-full.yml")
MINIMAL_PATH = Path(".github/workflows/phase1b-dev-minimal.yml")
APPROVAL_ENVIRONMENT = "international-benchmark-maintainer-approval"


def test_full_dev_workflow_is_manual_and_environment_gated() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.load(workflow_text, Loader=yaml.BaseLoader)

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    confirmation = workflow["on"]["workflow_dispatch"]["inputs"]["confirmation"]
    assert confirmation["required"] == "true"
    assert confirmation["options"] == ["full-dev-calibration-v2"]
    assert set(workflow["jobs"]) == {"plan", "shard", "aggregate"}
    assert all(job["environment"] == APPROVAL_ENVIRONMENT for job in workflow["jobs"].values())
    shard = workflow["jobs"]["shard"]
    assert int(shard["timeout-minutes"]) >= 180
    assert shard["strategy"]["fail-fast"] == "false"
    assert int(shard["strategy"]["max-parallel"]) == 20


def test_full_dev_workflow_uses_full_dev_only_and_calibration_v2() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "--calibration-v2" in workflow_text
    assert "--shard-size 1000" in workflow_text
    assert "--seed 20261106" in workflow_text
    assert "--sample-size" not in workflow_text
    assert "--max-shards" not in workflow_text
    assert "--minimal" not in workflow_text
    assert "split: test" not in workflow_text.lower()
    assert "--split test" not in workflow_text.lower()
    assert '["mdeberta", "minicheck", "factcg"]' in workflow_text
    assert 'assert manifest["sample_count"] == 30420' in workflow_text
    assert 'assert report["calibration_v2"]["certification_model_count"] == 1' in workflow_text
    assert "phase1b-dev-full-encrypted-*" in workflow_text
    assert "retention-days: 30" in workflow_text


def test_full_dev_workflow_reuses_exact_minimal_action_pins() -> None:
    full_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    minimal_text = MINIMAL_PATH.read_text(encoding="utf-8")
    action_prefixes = (
        "actions/checkout@",
        "actions/setup-python@",
        "actions/upload-artifact@",
        "actions/download-artifact@",
    )

    for action in action_prefixes:
        minimal_pins = {
            line.strip().split("#", 1)[0].strip()
            for line in minimal_text.splitlines()
            if line.strip().startswith("- uses: " + action)
        }
        full_pins = {
            line.strip().split("#", 1)[0].strip()
            for line in full_text.splitlines()
            if line.strip().startswith("- uses: " + action)
        }
        assert minimal_pins
        assert full_pins == minimal_pins


def test_full_dev_workflow_is_separate_from_minimal_workflow() -> None:
    assert WORKFLOW_PATH != MINIMAL_PATH
    assert WORKFLOW_PATH.is_file()
    assert MINIMAL_PATH.is_file()
