"""Dependabot must not propose changes that break provenance or the image lock."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))


def _update(ecosystem: str) -> dict[str, object]:
    (update,) = [u for u in CONFIG["updates"] if u["package-ecosystem"] == ecosystem]
    return update


def test_the_historical_benchmark_environment_is_not_updated() -> None:
    pip = _update("pip")
    assert pip["directory"] == "/"
    excluded = pip["exclude-paths"]
    assert "requirements-benchmark-pilot.txt" in excluded
    for path in excluded:
        assert (ROOT / pip["directory"].lstrip("/") / path).is_file(), path


def test_the_image_python_line_is_held_to_the_lock() -> None:
    docker = _update("docker")
    assert docker["directory"] == "/docker"
    (rule,) = [r for r in docker["ignore"] if r["dependency-name"] == "python"]
    assert set(rule["update-types"]) == {
        "version-update:semver-major",
        "version-update:semver-minor",
    }
    dockerfile = (ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.12-slim@sha256:" in dockerfile
    lock = (ROOT / "docker" / "requirements.lock").read_text(encoding="utf-8")
    assert "--hash=sha256:" in lock


def test_every_update_runs_weekly() -> None:
    assert {u["schedule"]["interval"] for u in CONFIG["updates"]} == {"weekly"}
