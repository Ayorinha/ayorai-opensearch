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


def test_cli_search_completed_without_verdict_exits_zero(monkeypatch) -> None:
    monkeypatch.setenv("ATTRACTOR_PROVIDER", "mock")
    result = CliRunner().invoke(cli_main.app, ["search", "consulta de teste da cli"])

    assert result.exit_code == cli_main.EXIT_OK
    payload = json.loads(result.stdout)
    assert payload["operation_status"] == "completed"
    # Not adjudicated is a property of the result, not an execution error.
    assert payload["verdict_authority"] == "not_adjudicated"


def test_cli_search_failed_operation_exits_nonzero_and_still_prints_json(monkeypatch) -> None:
    monkeypatch.setenv("ATTRACTOR_PROVIDER", "unsupported-provider")
    result = CliRunner().invoke(cli_main.app, ["search", "consulta de teste da cli"])

    assert result.exit_code == cli_main.EXIT_OPERATION_FAILED
    payload = json.loads(result.stdout)
    assert payload["operation_status"] == "failed"
    assert "Unsupported ATTRACTOR_PROVIDER" in payload["failures"][0]["message"]


def test_cli_search_invalid_input_exits_two_without_json(monkeypatch) -> None:
    monkeypatch.setenv("ATTRACTOR_PROVIDER", "mock")
    result = CliRunner().invoke(cli_main.app, ["search", "x"])

    assert result.exit_code == cli_main.EXIT_INVALID_INPUT
    assert result.stdout == ""
    assert "invalid query" in result.stderr


def test_opensearch_console_script_runs_the_search_command() -> None:
    import subprocess
    import sys
    import tomllib

    scripts = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
        "scripts"
    ]
    assert scripts["opensearch"] == "ayorai_attractor.cli.main:opensearch_entrypoint"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from ayorai_attractor.cli.main import opensearch_entrypoint; "
            "sys.argv = ['opensearch', 'consulta pelo entrypoint']; opensearch_entrypoint()",
        ],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "ATTRACTOR_PROVIDER": "mock"},
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["query"] == "consulta pelo entrypoint"
