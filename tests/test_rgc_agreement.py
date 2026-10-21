"""Synthetic unit tests for human annotator agreement; no real annotations."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
AGREEMENT: dict[str, Any] = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_agreement.py"))


def test_perfect_agreement_passes_point_estimate_gate_and_reports_matrix() -> None:
    labels = {
        "a": "SUPPORTED",
        "b": "REFUTED",
        "c": "UNVERIFIED",
        "d": "PARTIALLY_SUPPORTED",
        "e": "CONFLICTING",
    }
    result = AGREEMENT["compute_agreement"](labels, labels, iterations=100)
    assert result["cohen_kappa"] == 1.0
    assert result["gate_passed"] is True
    assert result["observed_agreement"] == 1.0
    assert result["confusion_matrix"]["SUPPORTED"]["SUPPORTED"] == 1
    assert result["class_distribution"]["CONFLICTING"]["agreements"] == 1
    assert result["ci95_case_bootstrap"] == [1.0, 1.0]


def test_balanced_cross_disagreement_has_zero_kappa() -> None:
    labels_a = {"a": "SUPPORTED", "b": "SUPPORTED", "c": "REFUTED", "d": "REFUTED"}
    labels_b = {"a": "SUPPORTED", "b": "REFUTED", "c": "SUPPORTED", "d": "REFUTED"}
    result = AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=100)
    assert result["cohen_kappa"] == 0.0
    assert result["gate_passed"] is False
    assert result["observed_agreement"] == 0.5


def test_rule_gap_is_excluded_if_either_annotator_marks_it() -> None:
    labels_a = {"a": "SUPPORTED", "b": "REFUTED", "c": "RULE_GAP"}
    labels_b = {"a": "SUPPORTED", "b": "REFUTED", "c": "SUPPORTED"}
    result = AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=100)
    assert result["n_eligible"] == 2
    assert result["n_rule_gap_excluded"] == 1
    assert result["rule_gap_excluded_disagreements"] == 1
    assert result["rule_gap_excluded_case_ids"] == ["c"]
    assert result["cohen_kappa"] == 1.0


def test_annotation_ids_must_match_exactly() -> None:
    with pytest.raises(ValueError, match="case IDs differ"):
        AGREEMENT["compute_agreement"]({"a": "SUPPORTED"}, {"b": "SUPPORTED"}, iterations=10)


def test_duplicate_annotation_id_is_rejected(tmp_path: Path) -> None:
    file_path = tmp_path / "annotations.jsonl"
    file_path.write_text(
        '{"case_id":"a","label":"SUPPORTED"}\n{"case_id":"a","label":"REFUTED"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate case_id"):
        AGREEMENT["load_annotations"](file_path)


def test_bootstrap_interval_is_deterministic() -> None:
    labels_a = {f"case-{i}": "SUPPORTED" if i < 10 else "REFUTED" for i in range(20)}
    labels_b = dict(labels_a)
    labels_b["case-3"] = "REFUTED"
    first = AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=250, seed=17)
    second = AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=250, seed=17)
    assert first["ci95_case_bootstrap"] == second["ci95_case_bootstrap"]
    assert first["bootstrap"] == second["bootstrap"]


def test_unknown_label_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid labels"):
        AGREEMENT["compute_agreement"]({"a": "NOT_A_LABEL"}, {"a": "SUPPORTED"}, iterations=10)


def test_bootstrap_iterations_must_be_positive() -> None:
    with pytest.raises(ValueError, match="iterations must be positive"):
        AGREEMENT["compute_agreement"]({"a": "SUPPORTED"}, {"a": "SUPPORTED"}, iterations=0)


def test_all_rule_gap_pairs_abort_instead_of_returning_a_kappa() -> None:
    labels_a = {"a": "RULE_GAP"}
    labels_b = {"a": "RULE_GAP"}
    with pytest.raises(ValueError, match="no eligible cases remain"):
        AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=10)


def test_kappa_is_undefined_without_marginal_variation_and_does_not_pass_gate() -> None:
    labels = {"a": "SUPPORTED", "b": "SUPPORTED", "c": "SUPPORTED"}
    result = AGREEMENT["compute_agreement"](labels, labels, iterations=100)
    assert result["cohen_kappa"] is None
    assert result["gate_passed"] is False
    assert result["ci95_case_bootstrap"] is None
