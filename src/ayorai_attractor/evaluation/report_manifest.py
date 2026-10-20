"""Deterministic integrity manifest for generated evaluation reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from collections.abc import Sequence


def build_artifact_manifest(
    json_path: Path,
    markdown_path: Path,
    *,
    commit: str,
    selected_suites: Sequence[str],
) -> dict[str, object]:
    """Hash final artifact bytes from outside the artifacts they describe."""
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
