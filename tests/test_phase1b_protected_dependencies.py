"""S-07: jobs that hold the Phase 1b keys install only hash-verified dependencies.

The jobs that run no model inference (plan, aggregate, re-aggregate, cache experiment)
hold the gold-label and/or artifact keys and install a hash lock. The inference job
(shard) holds the artifact key; since P4-01 it installs the historical versions
(docs/security/HISTORICAL-PINS.md) from two hash locks: PyTorch CPU from the official
CPU index and the rest from PyPI. It never receives the gold-label key.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements-phase1b-protected.txt"
INFERENCE_LOCK = ROOT / "requirements-phase1b-inference.txt"
TORCH_LOCK = ROOT / "requirements-phase1b-torch-cpu.txt"
HISTORICAL = ROOT / "reproducibility" / "phase1b-dev-2026-11-07" / "MANIFEST.json"
INFERENCE_INSTALLS = [
    "python -m pip install --require-hashes --only-binary :all: --no-deps "
    "--index-url https://download.pytorch.org/whl/cpu -r requirements-phase1b-torch-cpu.txt",
    "python -m pip install --require-hashes --only-binary :all: --no-deps "
    "--index-url https://pypi.org/simple -r requirements-phase1b-inference.txt",
]
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


def _lock_pins(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    return {
        name.lower().replace("_", "-"): version
        for name, version in re.findall(
            r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\]+)", text, re.MULTILINE
        )
    }


def _hash_blocks(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return re.split(r"\n(?=[A-Za-z0-9][A-Za-z0-9._-]*==)", text[text.index("\n\n") :].strip())


def test_inference_locks_hash_every_package() -> None:
    for path in (INFERENCE_LOCK, TORCH_LOCK):
        blocks = _hash_blocks(path)
        assert len(blocks) == len(_lock_pins(path)) > 0, path.name
        for block in blocks:
            assert re.search(r"--hash=sha256:[0-9a-f]{64}", block), (path.name, block)


def test_inference_locks_hold_the_historical_environment() -> None:
    record = json.loads(HISTORICAL.read_text(encoding="utf-8"))
    historical = {
        name.lower().replace("_", "-"): version
        for name, version in record["environments"]["inference"]["packages"].items()
    }
    pins = {**_lock_pins(INFERENCE_LOCK), **_lock_pins(TORCH_LOCK)}
    # Same environment as the historical runs, except the patched cryptography.
    assert pins.pop("cryptography") == "50.0.2"
    assert historical.pop("cryptography") == "46.0.3"
    assert pins == historical


def test_inference_job_installs_only_the_hash_locks() -> None:
    for name in ("phase1b-dev-full.yml", "phase1b-dev-minimal.yml"):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text("utf-8"))
        run = "\n".join(_install_steps(workflow["jobs"]["shard"]))
        lines = [
            line.strip()
            for line in run.splitlines()
            if "pip install" in line and 'install "pip==' not in line
        ]
        assert lines == INFERENCE_INSTALLS, (name, lines)
        assert "python -m pip check" in run
        assert "requirements-benchmark-pilot.txt" not in run
        assert not any(
            "PHASE1B_GOLD_LABEL_ENCRYPTION_KEY" in (step.get("env") or {})
            for step in workflow["jobs"]["shard"]["steps"]
        )


def test_every_job_that_receives_a_phase1b_key_installs_only_hash_locks() -> None:
    for path in sorted((ROOT / ".github" / "workflows").glob("phase1b-*.yml")):
        workflow = yaml.safe_load(path.read_text("utf-8"))
        for job_name, job in workflow["jobs"].items():
            if "secrets.PHASE1B_" not in yaml.safe_dump(job):
                continue
            for run in _install_steps(job):
                for line in run.splitlines():
                    line = line.strip()
                    if "pip install" in line and 'install "pip==' not in line:
                        assert "--require-hashes" in line, (path.name, job_name, line)


def test_no_workflow_installs_the_vulnerable_cryptography() -> None:
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        assert "cryptography==46." not in path.read_text(encoding="utf-8"), path.name
