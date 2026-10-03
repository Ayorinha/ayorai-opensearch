# ruff: noqa
from pathlib import Path
from ayorai_attractor.evaluation.golden import evaluate_golden_v0

def test_golden_v0_uses_claim_text_and_reports_statistics() -> None:
    root=Path(__file__).resolve().parents[1]
    report=evaluate_golden_v0(root/"evals/golden/v0.jsonl",root/"evals/corpus/documents.jsonl")
    assert report["case_count"]==34
    assert report["cases_with_global_verdict"]==30
    assert report["network"] is False
    assert set(report["confusion_matrix"])=={"VERIFIED","SUPPORTED","PARTIALLY_SUPPORTED","UNVERIFIED","REFUTED","CONFLICTING"}
    assert report["bootstrap_95_ci"]["iterations"]==10000
    assert report["mcnemar_vs_legacy"]["exact_p"]>=0
    assert report["abstention_contracts"]["evaluated"] is True
