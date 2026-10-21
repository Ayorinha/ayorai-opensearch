from __future__ import annotations

import runpy

import pytest

KAPPA = runpy.run_path("scripts/kappa_golden_pt.py")


def test_agreement_reports_unweighted_kappa_ci_matrix_and_rule_gap_exclusion() -> None:
    annotator_a = {
        "c1": "SUPPORTED",
        "c2": "SUPPORTED",
        "c3": "REFUTED",
        "c4": "REFUTED",
        "pilot-gap": "RULE_GAP",
    }
    annotator_b = {
        "c1": "SUPPORTED",
        "c2": "REFUTED",
        "c3": "REFUTED",
        "c4": "REFUTED",
        "pilot-gap": "SUPPORTED",
    }

    report = KAPPA["calculate_agreement"](annotator_a, annotator_b, iterations=200)

    assert report["n_included"] == 4
    assert report["n_rule_gap_excluded"] == 1
    assert report["rule_gap_case_ids"] == ["pilot-gap"]
    assert report["cohen_kappa_unweighted"] == pytest.approx(0.5)
    assert report["kappa_ci95_percentile"] is not None
    assert report["bootstrap_valid_replicates"] > 0
    assert report["observed_agreement"] == pytest.approx(0.75)
    assert report["confusion_matrix"]["SUPPORTED"]["SUPPORTED"] == 1
    assert report["confusion_matrix"]["SUPPORTED"]["REFUTED"] == 1
    assert report["gate_passed"] is False


def test_agreement_rejects_missing_annotation_records() -> None:
    with pytest.raises(ValueError, match="conjuntos de ids"):
        KAPPA["calculate_agreement"](
            {"case-1": "SUPPORTED", "case-2": "REFUTED"},
            {"case-1": "SUPPORTED"},
            iterations=50,
        )


def test_agreement_rejects_unknown_labels() -> None:
    with pytest.raises(ValueError, match="rótulo inválido"):
        KAPPA["calculate_agreement"](
            {"case-1": "UNKNOWN"},
            {"case-1": "SUPPORTED"},
            iterations=50,
        )
