from pathlib import Path

from scripts.lint_golden import lint_golden


def test_golden_v0_lint_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    errors = lint_golden(
        root / "evals/golden/v0.jsonl",
        root / "evals/corpus/documents.jsonl",
    )
    assert errors == []
