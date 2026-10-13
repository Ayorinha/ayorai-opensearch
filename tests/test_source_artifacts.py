"""Integrity guard: every verified source artifact must exist and match its SHA-256."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "evals" / "ptbr" / "SOURCES-REGISTRY.json"
MANIFEST_PATH = ROOT / "evals" / "ptbr" / "sources" / "raw" / "CAPTURE-MANIFEST.json"


def _verified_sources() -> list[dict[str, object]]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return [s for s in registry["sources"] if s["status"] == "verified"]


def test_verified_artifacts_exist_and_match_sha256() -> None:
    sources = _verified_sources()
    assert sources, "expected at least one verified source"
    for source in sources:
        path = ROOT / str(source["artifact_path"])
        assert path.is_file(), f"missing artifact for {source['source_id']}: {path}"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == source["sha256"], f"SHA-256 mismatch for {source['source_id']}"


def test_registry_matches_capture_manifest() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_path = {r["artifact_path"]: r for r in manifest["records"] if "artifact_path" in r}
    for source in _verified_sources():
        record = by_path[source["artifact_path"]]
        assert record["sha256"] == source["sha256"]
        assert record["retrieved_at"] == source["retrieved_at"]
        assert record["status"] == 200
