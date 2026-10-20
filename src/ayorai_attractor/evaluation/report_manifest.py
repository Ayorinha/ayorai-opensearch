"""Deterministic integrity manifest for generated evaluation reports."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path


def build_artifact_manifest(
    json_path: Path,
    markdown_path: Path,
    *,
    commit: str,
    selected_suites: Sequence[str],
) -> dict[str, object]:
    """Hash final artifact bytes from outside the artifacts they describe."""
    if not commit.strip():
        raise ValueError("commit must be non-empty")
    if not selected_suites or any(not suite.strip() for suite in selected_suites):
        raise ValueError("selected_suites must contain non-empty suite names")
    if len(set(selected_suites)) != len(selected_suites):
        raise ValueError("selected_suites must not contain duplicates")
    if json_path.resolve() == markdown_path.resolve():
        raise ValueError("JSON and Markdown artifacts must be different files")
    if json_path.name == markdown_path.name:
        raise ValueError("artifact filenames must be unique in the manifest")
    artifacts: dict[str, dict[str, str | int]] = {}
    for path in (json_path, markdown_path):
        artifacts[path.name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_bytes": path.stat().st_size,
        }
    return {
        "schema_version": "1",
        "commit": commit,
        "selected_suites": list(selected_suites),
        "artifacts": artifacts,
    }


def write_artifact_manifest(
    json_path: Path,
    markdown_path: Path,
    manifest_path: Path,
    *,
    commit: str,
    selected_suites: Sequence[str],
) -> dict[str, object]:
    if manifest_path.resolve() in {json_path.resolve(), markdown_path.resolve()}:
        raise ValueError("manifest path must be separate from artifact paths")
    manifest = build_artifact_manifest(
        json_path,
        markdown_path,
        commit=commit,
        selected_suites=selected_suites,
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
