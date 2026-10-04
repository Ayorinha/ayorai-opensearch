import json
from pathlib import Path
from runpy import run_path

import pytest


_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_training_manifest.py"
check_manifest = run_path(str(_MODULE_PATH))["check_manifest"]


def test_real_manifest_passes() -> None:
    with open("configs/training-data-manifest.json", encoding="utf-8") as file:
        data = json.load(file)
    assert check_manifest(data) == []


def valid_entry() -> dict[str, str]:
    return {
        "source": "data/train.jsonl",
        "license": "MIT",
        "license_status": "COMMERCIAL_DEFAULT",
        "sha256": "a" * 64,
        "provenance_url": "https://example.com/source",
    }


def test_missing_field() -> None:
    entry = valid_entry()
    del entry["source"]
    errors = check_manifest({"version": 1, "entries": [entry]})
    assert any("missing field source" in error for error in errors)


def test_license_status_error() -> None:
    entry = valid_entry()
    entry["license_status"] = "EVAL_ONLY"
    errors = check_manifest({"version": 1, "entries": [entry]})
    assert any("license_status" in error for error in errors)


@pytest.mark.parametrize("sha", ["A" * 64, "f" * 63, "g" * 64])
def test_sha256_error(sha: str) -> None:
    entry = valid_entry()
    entry["sha256"] = sha
    errors = check_manifest({"version": 1, "entries": [entry]})
    assert any("sha256" in error for error in errors)


def test_eval_source_error() -> None:
    entry = valid_entry()
    entry["source"] = "evals/golden.jsonl"
    errors = check_manifest({"version": 1, "entries": [entry]})
    assert any("evals/" in error for error in errors)


def test_missing_entries() -> None:
    errors = check_manifest({"version": 1})
    assert errors == ["manifest: missing entries"]


def test_entries_must_be_list() -> None:
    errors = check_manifest({"version": 1, "entries": {}})
    assert errors == ["manifest: entries must be a list"]


def test_entry_must_be_object() -> None:
    errors = check_manifest({"version": 1, "entries": ["invalid"]})
    assert errors == ["entry 0: must be an object"]
