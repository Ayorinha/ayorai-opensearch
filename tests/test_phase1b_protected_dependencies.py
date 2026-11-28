"""S-07: jobs that hold the Phase 1b keys install only hash-verified dependencies.

The jobs that run no model inference (plan, aggregate, re-aggregate, cache experiment)
hold the gold-label and/or artifact keys and install a hash lock. The inference job
keeps the historical pins for numerical reproducibility (docs/security/HISTORICAL-PINS.md)
and never receives the gold-label key.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements-phase1b-protected.txt"
INSTALL = (
    "python -m pip install --require-hashes --only-binary :all: "
    "--index-url https://pypi.org/simple -r requirements-phase1b-protected.txt"
)
PROTECTED_JOBS = {
    "phase1b-dev-full.yml": ("plan", "aggregate"),
    "phase1b-dev-minimal.yml": ("plan", "aggregate"),
    "phase1b-dev-full-reaggregate.yml": ("aggregate",),
    "phase1b-dev-cache-experiment.yml": ("experiment",),
}


def _pins() -> dict[str, str]:
    text = LOCK.read_text(encoding="utf-8")
    return dict(re.findall(r"^([a-z0-9][a-z0-9._-]*)==([^\s\\]+) \\$", text, re.MULTILINE))


def _install_steps(job: dict) -> list[str]:
    return [step["run"] for step in job["steps"] if "pip install" in step.get("run", "")]


def test_every_locked_package_has_a_sha256_hash() -> None:
    text = LOCK.read_text(encoding="utf-8")
    blocks = re.split(r"\n(?=[a-z0-9][a-z0-9._-]*==)", text.split("\n\n", 1)[1].strip())
    assert len(blocks) == len(_pins()) > 0
    for block in blocks:
        assert re.search(r"--hash=sha256:[0-9a-f]{64}", block), block.splitlines()[0]


def test_lock_holds_the_patched_versions() -> None:
    pins = _pins()
    # The product range (pyproject) and the protected jobs must agree on cryptography.
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "cryptography>=50,<51" in project["project"]["dependencies"]
    assert pins["cryptography"].startswith("50.")
    # PYSEC-2026-113 is fixed in pyarrow 23.0.1; the plan job reads the DEV parquet.
    assert tuple(int(part) for part in pins["pyarrow"].split(".")) >= (23, 0, 1)
    assert {"huggingface-hub", "numpy"} <= set(pins)


def test_key_holding_jobs_install_only_the_hash_lock() -> None:
    for name, jobs in PROTECTED_JOBS.items():
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text("utf-8"))
        for job_name in jobs:
            installs = _install_steps(workflow["jobs"][job_name])
            assert installs, (name, job_name)
            for run in installs:
                lines = [
                    line.strip()
                    for line in run.splitlines()
                    if "pip install" in line and 'install "pip==' not in line
                ]
                assert lines == [INSTALL], (name, job_name, lines)


def test_inference_job_keeps_historical_pins_and_patched_cryptography() -> None:
    for name in ("phase1b-dev-full.yml", "phase1b-dev-minimal.yml"):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text("utf-8"))
        run = "\n".join(_install_steps(workflow["jobs"]["shard"]))
        assert "-r requirements-benchmark-pilot.txt cryptography==50.0.2" in run
        assert "46.0.3" not in run
        assert not any(
            "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY" in (step.get("env") or {})
            for step in workflow["jobs"]["shard"]["steps"]
        )


def test_no_workflow_installs_the_vulnerable_cryptography() -> None:
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        assert "cryptography==46." not in path.read_text(encoding="utf-8"), path.name
