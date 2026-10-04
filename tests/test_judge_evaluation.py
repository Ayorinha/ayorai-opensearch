from pathlib import Path

from ayorai_attractor.evaluation.judge import evaluate_judge_suite


def test_judge_evaluation_covers_all_six_verdicts() -> None:
    root = Path(__file__).resolve().parents[1]
    report = evaluate_judge_suite(root / "evals/judge/v0.jsonl")

    assert report["case_count"] == 6
    assert report["correct"] == 6
    assert report["accuracy"] == 1.0
    assert set(report["results"][i]["predicted"] for i in range(6)) == {
        "VERIFIED",
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "CONFLICTING",
        "REFUTED",
        "UNVERIFIED",
    }


def test_golden_v1_provenance_edge_stays_supported() -> None:
    root = Path(__file__).resolve().parents[1]
    report = evaluate_judge_suite(root / "evals/golden/judge-smoke.jsonl")

    assert report["case_count"] == 1
    assert report["correct"] == 1
    assert report["results"][0]["predicted"] == "SUPPORTED"
