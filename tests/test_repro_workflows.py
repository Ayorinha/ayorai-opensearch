"""DEV producer workflows must install the recorded historical environment only."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
RECORD = "reproducibility/phase1b-dev-2026-11-07"
CHECK = f"python scripts/repro/check_environment.py {RECORD}/MANIFEST.json"

# (workflow, job) -> environment recorded in MANIFEST.json
EXPECTED = {
    ("phase1b-dev-full.yml", "plan"): "plan",
    ("phase1b-dev-full.yml", "shard"): "inference",
    ("phase1b-dev-full.yml", "aggregate"): "aggregate",
    ("phase1b-dev-full-reaggregate.yml", "aggregate"): "aggregate",
    ("phase1b-dev-minimal.yml", "plan"): "plan",
    ("phase1b-dev-minimal.yml", "shard"): "inference",
    ("phase1b-dev-minimal.yml", "aggregate"): "aggregate",
}
BENCHMARK_SCRIPTS = ("scripts/benchmarks/", "score_cache.py", "aggregate_dev.py")


def _jobs(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))["jobs"]


def _run_text(step: dict) -> str:
    return str(step.get("run", ""))


@pytest.mark.parametrize(("workflow", "job", "environment"), [(*k, v) for k, v in EXPECTED.items()])
def test_producer_job_installs_hash_locked_environment_before_benchmark_code(
    workflow: str, job: str, environment: str
) -> None:
    steps = _jobs(workflow)[job]["steps"]
    install = next(i for i, s in enumerate(steps) if "--require-hashes" in _run_text(s))
    text = _run_text(steps[install])
    lock = "aggregate" if environment == "aggregate" else "inference"
    assert f"-r {RECORD}/{lock}-requirements.lock.txt" in text
    assert "--no-deps" in text
    check = next(i for i, s in enumerate(steps) if CHECK in _run_text(s))
    assert f"{CHECK} {environment}" in _run_text(steps[check])
    assert install <= check
    first_benchmark = min(
        (
            i
            for i, s in enumerate(steps)
            if any(token in _run_text(s) for token in BENCHMARK_SCRIPTS)
        ),
        default=len(steps),
    )
    assert check < first_benchmark


def test_cache_experiment_jobs_use_the_aggregate_lock() -> None:
    jobs = _jobs("phase1b-dev-cache-experiment.yml")
    for name, job in jobs.items():
        steps = job["steps"]
        texts = [_run_text(s) for s in steps]
        assert any(f"-r {RECORD}/aggregate-requirements.lock.txt" in t for t in texts), name
        assert any(f"{CHECK} aggregate" in t for t in texts), name


@pytest.mark.parametrize(
    "workflow",
    [
        "phase1b-dev-full.yml",
        "phase1b-dev-full-reaggregate.yml",
        "phase1b-dev-cache-experiment.yml",
        "phase1b-dev-minimal.yml",
    ],
)
def test_producers_no_longer_install_mutable_pins(workflow: str) -> None:
    text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
    assert "requirements-benchmark-pilot.txt" not in text
    assert "cryptography==46.0.3 numpy==2.2.6" not in text



def test_nltk_394_occurs_only_in_the_historical_inference_lock() -> None:
    pin = "nltk" + "==" + "3.9.4"
    allowed = RECORD + "/inference-requirements.lock.txt"
    text_suffixes = {".md", ".py", ".json", ".toml", ".txt", ".yml", ".yaml", ".ini", ".cfg"}
    ignored = {".git", ".venv", "__pycache__", ".pytest_cache"}
    candidates = (
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix in text_suffixes
        and not any(part in ignored for part in path.relative_to(ROOT).parts)
    )
    occurrences = []
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if pin in text:
            occurrences.append(path.relative_to(ROOT).as_posix())
    assert occurrences == [allowed]


@pytest.mark.parametrize("workflow", ["phase1b-dev-full.yml", "phase1b-dev-minimal.yml"])
def test_shard_torch_stays_cpu_only_and_pinned(workflow: str) -> None:
    steps = _jobs(workflow)["shard"]["steps"]
    text = "\n".join(_run_text(s) for s in steps)
    assert '--index-url https://download.pytorch.org/whl/cpu "torch==2.7.1"' in text
    assert "assert torch.version.cuda is None" in text


@pytest.mark.parametrize(
    "workflow",
    [
        "phase1b-dev-full.yml",
        "phase1b-dev-full-reaggregate.yml",
        "phase1b-dev-cache-experiment.yml",
        "phase1b-dev-minimal.yml",
    ],
)
def test_producers_pin_the_recorded_python_patch_version(workflow: str) -> None:
    for job in _jobs(workflow).values():
        for step in job["steps"]:
            if str(step.get("uses", "")).startswith("actions/setup-python@"):
                assert step["with"]["python-version"] == "3.12.16"
