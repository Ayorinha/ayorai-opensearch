from __future__ import annotations

import hashlib
import json
import runpy
import sys
from pathlib import Path
from typing import Any


def test_runner_writes_consistent_json_markdown_and_manifest(
    tmp_path: Path, monkeypatch: Any
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    scripts_dir = repo_root / "scripts"
    monkeypatch.syspath_prepend(str(scripts_dir))
    namespace = runpy.run_path(str(scripts_dir / "run_h1_eval.py"), run_name="h1_eval_runner_test")

    eval_root = tmp_path / "evals"
    golden_dir = eval_root / "golden"
    golden_dir.mkdir(parents=True)
    (golden_dir / "v0.jsonl").write_text('{"id":"case-0"}\n', encoding="utf-8")
    (golden_dir / "v0.1.jsonl").write_text('{"id":"case-1"}\n', encoding="utf-8")
    corpus_path = eval_root / "corpus" / "documents.jsonl"
    corpus_path.parent.mkdir(parents=True)
    corpus_path.write_text('{"doc_id":"doc-1"}\n', encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()

    def fake_load_jsonl(path: Path) -> list[dict[str, Any]]:
        return [{"doc_id": "doc-1", "id": "case-0"}]

    def fake_metric_result() -> dict[str, Any]:
        return {
            "results": [
                {"id": "case-0", "expected": "SUPPORTED", "predicted": "SUPPORTED"}
            ],
            "accuracy": 1.0,
            "balanced_accuracy": 1.0,
            "macro_f1": 1.0,
            "bootstrap_95_ci": {"lower": 1.0, "upper": 1.0},
            "ece": 0.0,
            "latency_ms": {"p50": 1.0, "p95": 2.0},
        }

    def fake_suite(cases: list[dict[str, Any]], corpus: dict[str, dict[str, Any]]) -> dict[str, Any]:
        return {
            key: fake_metric_result()
            for key in ("A_baseline", "A_H1", "B_baseline", "B_H1")
        }

    monkeypatch.setitem(namespace, "ROOT", tmp_path)
    monkeypatch.setitem(namespace, "CORPUS", corpus_path)
    monkeypatch.setitem(namespace, "OUT_JSON", reports / "h1-results.json")
    monkeypatch.setitem(namespace, "OUT_MD", reports / "H1-RESULTS.md")
    monkeypatch.setitem(namespace, "OUT_MANIFEST", reports / "h1-results.manifest.json")
    monkeypatch.setitem(namespace, "_load_jsonl", fake_load_jsonl)
    monkeypatch.setitem(namespace, "_suite", fake_suite)
    monkeypatch.setattr(sys, "argv", ["run_h1_eval.py", "--suite", "golden-v0"])

    namespace["main"]()

    json_path = reports / "h1-results.json"
    markdown_path = reports / "H1-RESULTS.md"
    manifest_path = reports / "h1-results.manifest.json"
    report = json.loads(json_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert report["selected_suites"] == ["golden-v0"]
    assert report["golden_v0"] is not None
    assert report["golden_v0_1"] is None
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "## golden-v0" in markdown
    assert "## golden-v0.1" not in markdown
    assert manifest["selected_suites"] == ["golden-v0"]
    assert manifest["artifacts"][json_path.name]["sha256"] == hashlib.sha256(
        json_path.read_bytes()
    ).hexdigest()
    assert manifest["artifacts"][markdown_path.name]["sha256"] == hashlib.sha256(
        markdown_path.read_bytes()
    ).hexdigest()
