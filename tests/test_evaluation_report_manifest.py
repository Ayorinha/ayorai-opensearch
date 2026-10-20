from __future__ import annotations

import hashlib
import json
from pathlib import Path

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
    assert before["artifacts"]["results.json"]["sha256"] != after["artifacts"]["results.json"]["sha256"]
