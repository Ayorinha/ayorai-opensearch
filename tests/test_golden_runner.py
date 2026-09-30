from pathlib import Path

from ayorai_attractor.evaluation.golden import evaluate_golden_v0


def test_golden_v0_runner_is_deterministic_and_closed_world() -> None:
    root = Path(__file__).resolve().parents[1]
    report = evaluate_golden_v0(
        root / "evals/golden/v0.jsonl",
        root / "evals/corpus/documents.jsonl",
    )
    assert report["case_count"] == 34
    assert report["corpus_document_count"] == 52
    assert report["global_accuracy"] == {
        "correct": 13,
        "total": 30,
        "accuracy": 0.433333,
    }
    assert report["majority_class_baseline"] == {
        "label": "PARTIALLY_SUPPORTED",
        "correct": 13,
        "total": 30,
        "accuracy": 0.433333,
    }
    assert report["network"] is False
