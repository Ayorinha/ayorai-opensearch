"""Synthetic-only tests for the pinned NLTK punkt_tab installer (no network, no real data)."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from scripts.benchmarks.phase1b.nltk_resources import (
    NLTK_PIN_PATH,
    install_from_zip_bytes,
    load_pin,
    verify_files,
)


def synthetic_archive() -> tuple[bytes, dict]:
    files = {
        "punkt_tab/english/abbrev_types.txt": b"synthetic abbrev\n",
        "punkt_tab/english/sent_starters.txt": b"synthetic starters\n",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr("punkt_tab/german/ignored.txt", b"not extracted")
    payload = buffer.getvalue()
    pin = {
        "nltk_version": "0.0-synthetic",
        "nltk_data_commit": "c" * 40,
        "source_url": "https://example.invalid/" + "c" * 40 + "/punkt_tab.zip",
        "zip_size_bytes": len(payload),
        "zip_sha256": hashlib.sha256(payload).hexdigest(),
        "files": {
            name: {"size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
            for name, content in files.items()
        },
    }
    return payload, pin


def test_repository_pin_is_complete_and_commit_pinned() -> None:
    pin = load_pin(NLTK_PIN_PATH)
    assert pin["nltk_version"] == "3.9.4"
    assert len(pin["zip_sha256"]) == 64
    assert pin["nltk_data_commit"] in pin["source_url"]
    assert all(name.startswith("punkt_tab/english/") for name in pin["files"])
    assert json.loads(NLTK_PIN_PATH.read_text(encoding="utf-8"))["status"].startswith("pinned")


def test_install_extracts_only_pinned_files_and_verifies(tmp_path: Path) -> None:
    payload, pin = synthetic_archive()
    install_from_zip_bytes(payload, pin, tmp_path)
    assert set(verify_files(pin, tmp_path)) == set(pin["files"])
    assert not (tmp_path / "tokenizers" / "punkt_tab" / "german").exists()


def test_install_rejects_tampered_archive(tmp_path: Path) -> None:
    payload, pin = synthetic_archive()
    with pytest.raises(ValueError):
        install_from_zip_bytes(payload + b"x", pin, tmp_path)
    pin_bad_hash = dict(pin, zip_sha256="0" * 64)
    with pytest.raises(ValueError):
        install_from_zip_bytes(payload, pin_bad_hash, tmp_path)


def test_verify_rejects_modified_or_missing_file(tmp_path: Path) -> None:
    payload, pin = synthetic_archive()
    install_from_zip_bytes(payload, pin, tmp_path)
    target = tmp_path / "tokenizers" / "punkt_tab" / "english" / "abbrev_types.txt"
    target.write_bytes(b"tampered\n")
    with pytest.raises(ValueError):
        verify_files(pin, tmp_path)
    target.unlink()
    with pytest.raises(ValueError):
        verify_files(pin, tmp_path)


def test_dev_fetch_validation_fails_closed(tmp_path: Path) -> None:
    from scripts.benchmarks.phase1b.common import DEV_PIN_PATH
    from scripts.benchmarks.phase1b.fetch_dev import validate_pin, verify_file

    pin = json.loads(DEV_PIN_PATH.read_text(encoding="utf-8"))
    validate_pin(pin)
    with pytest.raises(SystemExit):
        validate_pin(dict(pin, file="data/test-00000-of-00001.parquet"))
    fake = tmp_path / "fake.parquet"
    fake.write_bytes(b"synthetic")
    with pytest.raises(SystemExit):
        verify_file(fake, pin)
