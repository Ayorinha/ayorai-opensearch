"""Aggregate-only integration of preregistered Calibration V2 for Phase 1b."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from scripts.benchmarks.phase1b.calibration import (
    balanced_accuracy,
    calibrate_by_cohort,
)
from scripts.benchmarks.phase1b.calibration_v2 import (
    crossfit_folds,
    ivap_crossfit,
    learn_then_test,
    probabilistic_metrics,
    split_dev_a_b,
    venn_abers_reference,
)

MODEL_IDS = ("mdeberta", "minicheck", "factcg")
MODEL_COST_SECONDS = {"mdeberta": 1.8896, "minicheck": 4.2812, "factcg": 4.3036}
COHORTS = (
    "AggreFact-CNN",
    "AggreFact-XSum",
    "ClaimVerify",
    "ExpertQA",
    "FactCheck-GPT",
    "Lfqa",
    "RAGTruth",
    "Reveal",
    "TofuEval-MediaS",
    "TofuEval-MeetB",
    "Wice",
)


def _label(value: Any) -> int:
    if value in (1, "1", "SUPPORTED"):
        return 1
    if value in (0, "0", "NOT_SUPPORTED"):
        return 0
    raise ValueError("private shard contains an invalid gold label")


def _validated_model_rows(
    model_rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[list[str], list[str], list[int], dict[str, dict[str, float]]]:
    if set(model_rows) != set(MODEL_IDS):
        raise ValueError("Calibration V2 requires all three preregistered model outputs")
    reference: dict[str, tuple[int, str]] = {}
    scores_by_model: dict[str, dict[str, float]] = {}
    for model in MODEL_IDS:
        scores: dict[str, float] = {}
        for row in model_rows[model]:
            record_id = row.get("record_id")
            cohort = row.get("cohort")
            score = row.get("score")
            if not isinstance(record_id, str) or not record_id:
                raise ValueError("private calibration record lacks record_id")
            if cohort not in COHORTS:
                raise ValueError("private calibration record has an unknown dataset cohort")
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise ValueError("private calibration score must be numeric")
            value = float(score)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("private calibration score must be finite and in [0, 1]")
            label = _label(row.get("gold"))
            if record_id in scores:
                raise ValueError("duplicate record in model output")
            scores[record_id] = value
            identity = (label, cohort)
            if record_id in reference and reference[record_id] != identity:
                raise ValueError("model outputs disagree on label or cohort")
            reference[record_id] = identity
        scores_by_model[model] = scores

    expected_ids = set(reference)
    if not expected_ids or any(set(scores) != expected_ids for scores in scores_by_model.values()):
        raise ValueError("model outputs must contain the same complete DEV record set")
    record_ids = sorted(expected_ids)
    cohorts = [reference[record_id][1] for record_id in record_ids]
    labels = [reference[record_id][0] for record_id in record_ids]
    if set(cohorts) != set(COHORTS):
        raise ValueError("Calibration V2 requires the preregistered 11 DEV cohorts")
    return record_ids, cohorts, labels, scores_by_model


def _crossfit_threshold_ba(
    record_ids: Sequence[str],
    cohorts: Sequence[str],
    labels: Sequence[int],
    scores: Sequence[float],
    dev_a_indices: Sequence[int],
) -> dict[str, float]:
    ids = [record_ids[index] for index in dev_a_indices]
    ds = [cohorts[index] for index in dev_a_indices]
    ys = [labels[index] for index in dev_a_indices]
    values = [scores[index] for index in dev_a_indices]
    folds, limitations = crossfit_folds(ids, ds, ys)
    if limitations:
        raise ValueError("cross-fitting strata below five cases; candidate is ineligible")
    oof_predictions: dict[str, int] = {}
    for fold in sorted(set(folds.values())):
        train = [i for i, record_id in enumerate(ids) if folds[record_id] != fold]
        held = [i for i, record_id in enumerate(ids) if folds[record_id] == fold]
        thresholds = calibrate_by_cohort(
            [values[i] for i in train],
            [ys[i] for i in train],
            [ds[i] for i in train],
        )
        for index in held:
            threshold = thresholds.get(ds[index])
            if threshold is None:
                raise ValueError("held-out cohort has no eligible training threshold")
            oof_predictions[ids[index]] = int(values[index] > threshold)

    result: dict[str, float] = {}
    for cohort in sorted(set(ds)):
        cohort_ids = [ids[i] for i, value in enumerate(ds) if value == cohort]
        labels_by_record_id = dict(zip(ids, ys, strict=True))
        cohort_labels = [labels_by_record_id[record_id] for record_id in cohort_ids]
        predictions = [oof_predictions[record_id] for record_id in cohort_ids]
        result[cohort] = balanced_accuracy(cohort_labels, predictions)
    return result


def select_single_model(
    macro_ba_by_model: Mapping[str, float | None],
    *,
    costs: Mapping[str, float] = MODEL_COST_SECONDS,
) -> dict[str, Any]:
    """Apply eligibility, the strict <0.005 tie band, cost, and fixed priority."""
    if set(macro_ba_by_model) != set(MODEL_IDS):
        raise ValueError("selection requires exactly the three preregistered candidates")
    eligible: dict[str, float] = {}
    for model, value in macro_ba_by_model.items():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("macro BA must be numeric or None")
        if not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
            raise ValueError("macro BA must be finite and in [0, 1]")
        eligible[model] = float(value)
    if not eligible:
        raise ValueError("no eligible model candidate")
    best = max(eligible.values())
    tied = [model for model, value in eligible.items() if best - value < 0.005]
    priority = {model: index for index, model in enumerate(MODEL_IDS)}
    selected = min(tied, key=lambda model: (costs[model], priority[model]))
    return {
        "selected_model": selected,
        "macro_ba_by_model": dict(sorted(eligible.items())),
        "ineligible_models": sorted(set(MODEL_IDS) - set(eligible)),
        "maximum_macro_ba": best,
        "tie_band_strictly_below": 0.005,
        "tie_candidates": sorted(tied),
        "cost_seconds_per_example": {model: costs[model] for model in MODEL_IDS},
        "selection_rule": (
            "DEV-A macro dataset BA; strict <0.005 tie; lower pilot cost; fixed model priority"
        ),
    }


def _macro_dataset_mean(by_dataset: Mapping[str, Mapping[str, Any]], metric: str) -> float | None:
    values = [item[metric] for item in by_dataset.values()]
    if not values or any(value is None for value in values):
        return None
    return sum(float(value) for value in values) / len(values)


def calibration_v2_report(
    model_rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Compute V2 selection/calibration/certification and return aggregate-only data."""
    record_ids, cohorts, labels, score_maps = _validated_model_rows(model_rows)
    split_map, split_sha256 = split_dev_a_b(record_ids, cohorts)
    dev_a = [index for index, record_id in enumerate(record_ids) if split_map[record_id] == "DEV-A"]
    dev_b = [index for index, record_id in enumerate(record_ids) if split_map[record_id] == "DEV-B"]
    if not dev_a or not dev_b:
        raise ValueError("deterministic DEV-A/DEV-B split is empty")

    model_details: dict[str, Any] = {}
    macro_values: dict[str, float | None] = {}
    for model in MODEL_IDS:
        scores = [score_maps[model][record_id] for record_id in record_ids]
        try:
            ba_by_cohort = _crossfit_threshold_ba(record_ids, cohorts, labels, scores, dev_a)
            macro_ba = sum(ba_by_cohort.values()) / len(ba_by_cohort)
        except (ValueError, ZeroDivisionError):
            ba_by_cohort = {}
            macro_ba = None
        macro_values[model] = macro_ba

        ids_a = [record_ids[index] for index in dev_a]
        cohorts_a = [cohorts[index] for index in dev_a]
        labels_a = [labels[index] for index in dev_a]
        scores_a = [scores[index] for index in dev_a]
        folds_a, fold_limitations = crossfit_folds(ids_a, cohorts_a, labels_a)
        if fold_limitations:
            raise ValueError("DEV-A has crossfit strata below five; IVAP crossfit is unavailable")
        calibrated_a = ivap_crossfit(
            scores_a, labels_a, [folds_a[record_id] for record_id in ids_a]
        )
        metrics_by_cohort: dict[str, Any] = {}
        for cohort in COHORTS:
            indices = [i for i, value in enumerate(cohorts_a) if value == cohort]
            metrics_by_cohort[cohort] = probabilistic_metrics(
                [float(calibrated_a["p"][i]) for i in indices],
                [labels_a[i] for i in indices],
            )
        all_metrics = probabilistic_metrics([float(value) for value in calibrated_a["p"]], labels_a)
        model_details[model] = {
            "dev_a_crossfit_threshold_ba_by_dataset": ba_by_cohort,
            "dev_a_macro_dataset_crossfit_ba": macro_ba,
            "dev_a_crossfit_probability_metrics_by_dataset": metrics_by_cohort,
            "dev_a_crossfit_probability_metrics_all_cases": all_metrics,
            "crossfit_fold_limitations": fold_limitations,
        }

    selection = select_single_model(macro_values)
    selected = selection["selected_model"]
    selected_scores = score_maps[selected]
    calibration_indices = dev_a
    query_indices = dev_b
    fitted = venn_abers_reference(
        [selected_scores[record_ids[index]] for index in calibration_indices],
        [labels[index] for index in calibration_indices],
        [selected_scores[record_ids[index]] for index in query_indices],
    )
    ltt = learn_then_test(
        [float(value) for value in fitted["p"]],
        [labels[index] for index in query_indices],
        [cohorts[index] for index in query_indices],
        partition="dev_b",
        split="dev",
        calibration_fit="dev_a_full",
    )
    return {
        "schema_version": "phase1b-calibration-v2-aggregate-v1",
        "split": "dev",
        "dev_a_count": len(dev_a),
        "dev_b_count": len(dev_b),
        "split_mapping_sha256": split_sha256,
        "model_selection": selection,
        "models": model_details,
        "selected_model_dev_b_ltt": ltt,
        "certification_model_count": 1,
        "instance_level_output_published": False,
        "record_level_predictions_published": False,
    }
