"""Synthetic tests for the preregistered DEV-A single-model selection rule."""

from __future__ import annotations

import pytest

from scripts.benchmarks.phase1b.calibration_v2.aggregate import select_single_model


def test_selection_uses_strict_less_than_point005_tie_band_and_cost() -> None:
    result = select_single_model(
        {"mdeberta": 0.800, "minicheck": 0.796, "factcg": None},
        costs={"mdeberta": 2.0, "minicheck": 1.0, "factcg": 3.0},
    )
    assert result["selected_model"] == "minicheck"
    assert result["tie_candidates"] == ["mdeberta", "minicheck"]
    assert result["ineligible_models"] == ["factcg"]


def test_exact_point005_difference_is_not_a_tie() -> None:
    result = select_single_model(
        {"mdeberta": 0.800, "minicheck": 0.795, "factcg": None},
        costs={"mdeberta": 2.0, "minicheck": 1.0, "factcg": 3.0},
    )
    assert result["selected_model"] == "mdeberta"
    assert result["tie_candidates"] == ["mdeberta"]


def test_all_candidates_ineligible_fails_closed() -> None:
    with pytest.raises(ValueError, match="no eligible"):
        select_single_model({"mdeberta": None, "minicheck": None, "factcg": None})


def test_calibration_v2_requires_exact_candidate_set() -> None:
    with pytest.raises(ValueError, match="exactly"):
        select_single_model({"mdeberta": 0.8, "minicheck": 0.7})



def test_calibration_v2_report_end_to_end_aggregate_only() -> None:
    import json

    import numpy as np

    from scripts.benchmarks.phase1b.calibration_v2.aggregate import (
        COHORTS,
        MODEL_IDS,
        calibration_v2_report,
    )

    rng = np.random.default_rng(20261107)
    model_rows = {model: [] for model in MODEL_IDS}
    for cohort in COHORTS:
        labels = np.array([0] * 20 + [1] * 20, dtype=np.int8)
        rng.shuffle(labels)
        for index, label in enumerate(labels):
            record_id = f"synthetic-{cohort}-{index:02d}"
            for model in MODEL_IDS:
                if model == "mdeberta":
                    center = 0.08 if label == 0 else 0.92
                elif model == "minicheck":
                    center = 0.20 if label == 0 else 0.80
                else:
                    center = 0.12 if label == 0 else 0.88
                score = float(np.clip(center + rng.normal(0.0, 0.015), 0.0, 1.0))
                model_rows[model].append(
                    {
                        "record_id": record_id,
                        "cohort": cohort,
                        "gold": int(label),
                        "score": score,
                    }
                )

    report = calibration_v2_report(model_rows)
    serialized = json.dumps(report, sort_keys=True)
    expected_ids = {
        row["record_id"] for model_records in model_rows.values() for row in model_records
    }

    assert report["model_selection"]["selected_model"] == "mdeberta"
    assert report["certification_model_count"] == 1
    assert report["dev_a_count"] + report["dev_b_count"] == len(COHORTS) * 40
    assert len(COHORTS) == 11
    assert all(record_id not in serialized for record_id in expected_ids)



def test_calibration_v2_report_end_to_end_aggregate_only() -> None:
    import json

    import numpy as np

    from scripts.benchmarks.phase1b.calibration_v2.aggregate import (
        COHORTS,
        MODEL_IDS,
        calibration_v2_report,
    )

    rng = np.random.default_rng(20261107)
    model_rows = {model: [] for model in MODEL_IDS}
    for cohort in COHORTS:
        labels = np.array([0] * 20 + [1] * 20, dtype=np.int8)
        rng.shuffle(labels)
        for index, label in enumerate(labels):
            record_id = f"synthetic-{cohort}-{index:02d}"
            for model in MODEL_IDS:
                if model == "mdeberta":
                    center = 0.08 if label == 0 else 0.92
                elif model == "minicheck":
                    center = 0.20 if label == 0 else 0.80
                else:
                    center = 0.12 if label == 0 else 0.88
                score = float(np.clip(center + rng.normal(0.0, 0.015), 0.0, 1.0))
                model_rows[model].append(
                    {
                        "record_id": record_id,
                        "cohort": cohort,
                        "gold": int(label),
                        "score": score,
                    }
                )

    report = calibration_v2_report(model_rows)
    serialized = json.dumps(report, sort_keys=True)
    expected_ids = {
        row["record_id"] for model_records in model_rows.values() for row in model_records
    }

    assert report["model_selection"]["selected_model"] == "mdeberta"
    assert report["certification_model_count"] == 1
    assert report["dev_a_count"] + report["dev_b_count"] == len(COHORTS) * 40
    assert len(COHORTS) == 11
    assert all(record_id not in serialized for record_id in expected_ids)
