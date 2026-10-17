from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ayorai_attractor.cli import main as cli_main


def test_cli_help_exposes_search_and_eval_commands() -> None:
    result = CliRunner().invoke(cli_main.app, ["--help"])

    assert result.exit_code == 0
    assert "search" in result.stdout
    assert "eval" in result.stdout


def test_cli_eval_writes_json_report_for_supported_suite(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "reports" / "contract-report.json"
    calls: list[tuple[Path, Path, str]] = []

    def fake_evaluate(golden_path: Path, corpus_path: Path, *, suite: str):
        calls.append((golden_path, corpus_path, suite))
        return {"global_accuracy": 0.75, "majority_class_baseline": 0.5}

    monkeypatch.setattr(cli_main, "evaluate_golden_v0", fake_evaluate)
    result = CliRunner().invoke(
        cli_main.app,
        ["eval", "--suite", "golden-v0", "--out", str(output)],
    )

    assert result.exit_code == 0, result.stdout
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "global_accuracy": 0.75,
        "majority_class_baseline": 0.5,
    }
    assert len(calls) == 1
    assert calls[0][1] == Path("evals/corpus/documents.jsonl")
    assert calls[0][2] == "golden-v0"


def test_cli_eval_rejects_unsupported_suite_without_writing_output(
    tmp_path: Path,
) -> None:
    output = tmp_path / "must-not-exist.json"
    result = CliRunner().invoke(
        cli_main.app,
        ["eval", "--suite", "unsupported-suite", "--out", str(output)],
    )

    assert result.exit_code != 0
    assert not output.exists()
