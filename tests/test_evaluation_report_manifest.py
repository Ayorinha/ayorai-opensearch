from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ayorai_attractor.evaluation.report_manifest import (
    build_artifact_manifest,
    write_artifact_manifest,
)


def test_manifest_hashes_final_artifact_bytes(tmp_path: Path) -> None:
    json_path = tmp_path / "results.json"
    markdown_path = tmp_path / "results.md"
    manifest_path = tmp_path / "manifest.json"
    json_bytes = b'{"accuracy":0.75}\n'
    markdown_bytes = b"# Results\n"
    json_path.write_bytes(json_bytes)
    markdown_path.write_bytes(markdown_bytes)

    manifest = write_artifact_manifest(
        json_path,
        markdown_path,
        manifest_path,
        commit="abc123",
        selected_suites=("golden-v0.1",),
    )

    assert manifest["commit"] == "abc123"
    assert manifest["non_ci_run"] is False
    assert manifest["selected_suites"] == ["golden-v0.1"]
    assert manifest["artifacts"]["results.json"]["sha256"] == (
        hashlib.sha256(json_bytes).hexdigest()
    )
    assert manifest["artifacts"]["results.md"]["sha256"] == (
        hashlib.sha256(markdown_bytes).hexdigest()
    )
    assert manifest["artifacts"]["results.json"]["size_bytes"] == len(json_bytes)
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest


def test_manifest_changes_when_final_artifact_changes(tmp_path: Path) -> None:
    json_path = tmp_path / "results.json"
    markdown_path = tmp_path / "results.md"
    json_path.write_text("{}\n", encoding="utf-8")
    markdown_path.write_text("# Results\n", encoding="utf-8")
    before = build_artifact_manifest(
        json_path, markdown_path, commit="abc123", selected_suites=("golden-v0",)
    )
    json_path.write_text('{"changed":true}\n', encoding="utf-8")
    after = build_artifact_manifest(
        json_path, markdown_path, commit="abc123", selected_suites=("golden-v0",)
    )
    assert (
        before["artifacts"]["results.json"]["sha256"]
        != after["artifacts"]["results.json"]["sha256"]
    )


def test_manifest_rejects_output_path_that_would_overwrite_an_artifact(tmp_path: Path) -> None:
    json_path = tmp_path / "results.json"
    markdown_path = tmp_path / "results.md"
    json_path.write_text("{}\n", encoding="utf-8")
    markdown_path.write_text("# Results\n", encoding="utf-8")
    before = json_path.read_bytes()

    with pytest.raises(ValueError, match="separate from artifact paths"):
        write_artifact_manifest(
            json_path,
            markdown_path,
            json_path,
            commit="abc123",
            selected_suites=("golden-v0",),
        )

    assert json_path.read_bytes() == before


def test_manifest_rejects_duplicate_suite_names_and_empty_commit(tmp_path: Path) -> None:
    json_path = tmp_path / "results.json"
    markdown_path = tmp_path / "results.md"
    json_path.write_text("{}\n", encoding="utf-8")
    markdown_path.write_text("# Results\n", encoding="utf-8")

    with pytest.raises(ValueError, match="commit must be non-empty"):
        build_artifact_manifest(
            json_path, markdown_path, commit=" ", selected_suites=("golden-v0",)
        )
    with pytest.raises(ValueError, match="must not contain duplicates"):
        build_artifact_manifest(
            json_path,
            markdown_path,
            commit="abc123",
            selected_suites=("golden-v0", "golden-v0"),
        )


def test_manifest_requires_explicit_non_ci_marker_for_unknown_commit(tmp_path: Path) -> None:
    json_path = tmp_path / "results.json"
    markdown_path = tmp_path / "results.md"
    json_path.write_text("{}\n", encoding="utf-8")
    markdown_path.write_text("# Results\n", encoding="utf-8")

    with pytest.raises(
        ValueError, match="commit must be a known SHA unless non_ci_run is true"
    ):
        build_artifact_manifest(
            json_path,
            markdown_path,
            commit="unknown",
            selected_suites=("golden-v0",),
        )


def test_manifest_marks_unknown_commit_as_non_ci_run(tmp_path: Path) -> None:
    json_path = tmp_path / "results.json"
    markdown_path = tmp_path / "results.md"
    manifest_path = tmp_path / "manifest.json"
    json_path.write_text("{}\n", encoding="utf-8")
    markdown_path.write_text("# Results\n", encoding="utf-8")

    manifest = write_artifact_manifest(
        json_path,
        markdown_path,
        manifest_path,
        commit="unknown",
        selected_suites=("golden-v0",),
        non_ci_run=True,
    )

    assert manifest["commit"] == "unknown"
    assert manifest["non_ci_run"] is True
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest
