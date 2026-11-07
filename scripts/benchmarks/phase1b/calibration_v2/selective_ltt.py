"""Selective Learn then Test certification for pre-registered Calibration V2-3.

Certification accepts only DEV-B from the DEV split. Probabilities must have
been produced by fitting IVAP on all of DEV-A; this module never fits a
calibrator or reads DEV-A/TEST observations.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

RISK_LIMIT = 0.10
FAMILY_ALPHA = 0.05
N_COHORTS = 11
COHORT_ALPHA = FAMILY_ALPHA / N_COHORTS
MIN_ACCEPTED = 25
THRESHOLDS = tuple(index / 100 for index in range(99, 49, -1))


def _binomial_lower_tail_pvalue(errors: int, n: int) -> float:
    """Compute P(Binomial(n, 0.10) <= errors) with a log-space sum."""
    if isinstance(errors, bool) or not isinstance(errors, int):
        raise ValueError("errors must be an integer")
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n < 0 or errors < 0 or errors > n:
        raise ValueError("require 0 <= errors <= n")

    log_p = math.log(RISK_LIMIT)
    log_q = math.log1p(-RISK_LIMIT)
    log_terms = [
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
        + k * log_p
        + (n - k) * log_q
        for k in range(errors + 1)
    ]
    maximum = max(log_terms)
    log_total = maximum + math.log(
        math.fsum(math.exp(term - maximum) for term in log_terms)
    )
    return min(1.0, math.exp(log_total)) if log_total > math.log(5e-324) else 0.0


def _validated_inputs(
    probabilities: Sequence[float],
    labels: Sequence[int],
    cohorts: Sequence[str],
    partition: str,
    split: str,
    calibration_fit: str,
) -> tuple[Any, Any, Any]:
    import numpy as np

    if partition != "dev_b":
        raise ValueError("LTT certification requires partition='dev_b'")
    if split != "dev":
        raise ValueError("LTT certification requires split='dev'; TEST is forbidden")
    if calibration_fit != "dev_a_full":
        raise ValueError("probabilities must use IVAP fitted on all DEV-A, not cross-fit")

    probability_array = np.asarray(probabilities, dtype=np.float64)
    label_array = np.asarray(labels)
    cohort_array = np.asarray(cohorts)
    if (
        probability_array.ndim != 1
        or label_array.ndim != 1
        or cohort_array.ndim != 1
    ):
        raise ValueError("probabilities, labels and cohorts must be one-dimensional")
    if (
        probability_array.size == 0
        or probability_array.size != label_array.size
        or probability_array.size != cohort_array.size
    ):
        raise ValueError("probabilities, labels and cohorts must be non-empty and equally sized")
    if not np.isfinite(probability_array).all():
        raise ValueError("probabilities must be finite")
    if np.any((probability_array < 0.0) | (probability_array > 1.0)):
        raise ValueError("probabilities must be within [0, 1]")
    if label_array.dtype.kind not in "iu" or not np.isin(label_array, (0, 1)).all():
        raise ValueError("labels must contain binary integers 0 or 1")
    if cohort_array.dtype.kind not in "US" or any(
        not isinstance(value, str) or not value for value in cohorts
    ):
        raise ValueError("cohorts must contain non-empty strings")
    return probability_array, label_array.astype("int8"), cohort_array


def _threshold_result(
    probabilities: Any, labels: Any, threshold: float, total: int
) -> dict[str, Any]:
    import numpy as np

    confidence = np.maximum(probabilities, 1.0 - probabilities)
    accepted = confidence >= threshold
    supported = (probabilities >= threshold) & accepted
    predictions = supported.astype("int8")
    n_accepted = int(np.count_nonzero(accepted))
    errors = int(np.count_nonzero(predictions[accepted] != labels[accepted]))
    accuracy = (
        float((n_accepted - errors) / n_accepted) if n_accepted else None
    )
    return {
        "threshold": threshold,
        "n_total": total,
        "n_accepted": n_accepted,
        "coverage": n_accepted / total,
        "errors": errors,
        "error_rate": errors / n_accepted if n_accepted else None,
        "accuracy": accuracy,
        "accepted_mask": accepted,
    }


def _aurc(curve: Sequence[dict[str, Any]]) -> float | None:
    """Trapezoidal, unnormalised risk-coverage area over observed coverage > 0.

    Points are integrated in ascending coverage order. Equal-coverage points
    have zero horizontal width and therefore contribute no area. No area is
    extrapolated to coverage zero or beyond the largest observed coverage.
    """
    points = sorted(
        (
            (float(item["coverage"]), 1.0 - float(item["accuracy"]))
            for item in curve
            if item["coverage"] > 0.0 and item["accuracy"] is not None
        ),
        key=lambda point: point[0],
    )
    if len(points) < 2:
        return 0.0 if points else None
    area = math.fsum(
        (right_x - left_x) * (left_y + right_y) / 2.0
        for (left_x, left_y), (right_x, right_y) in zip(
            points, points[1:], strict=False
        )
    )
    return area


def learn_then_test(
    probabilities: Sequence[float],
    labels: Sequence[int],
    cohorts: Sequence[str],
    *,
    partition: str,
    split: str,
    calibration_fit: str,
) -> dict[str, Any]:
    """Certify per-cohort selective predictions using the fixed LTT sequence.

    Probabilities are P(SUPPORTED); labels use 1=SUPPORTED and 0=NOT_SUPPORTED.
    Input probabilities must be DEV-B predictions from an IVAP calibrator
    fitted on all DEV-A (calibration_fit="dev_a_full"). DEV-B is certification-only;
    DEV-A cross-fit predictions and TEST are rejected.
    The sequence is t=0.99,...,0.50; it stops at the first ineligible or
    non-rejected threshold. The certified threshold is the smallest rejected
    threshold reached before stopping. Later curve points are descriptive only.
    """
    probability_array, label_array, cohort_array = _validated_inputs(
        probabilities, labels, cohorts, partition, split, calibration_fit
    )
    results: dict[str, Any] = {}
    for cohort in sorted(set(cohort_array.tolist())):
        cohort_mask = cohort_array == cohort
        cohort_probabilities = probability_array[cohort_mask]
        cohort_labels = label_array[cohort_mask]
        total = int(cohort_probabilities.size)
        curve: list[dict[str, Any]] = []
        certified_threshold: float | None = None
        stop_reason: str | None = None
        tested_thresholds: list[float] = []

        for threshold in THRESHOLDS:
            point = _threshold_result(
                cohort_probabilities, cohort_labels, threshold, total
            )
            n_accepted = point["n_accepted"]
            point["p_value"] = None
            point["decision"] = "descriptive"
            if stop_reason is None:
                if n_accepted < MIN_ACCEPTED:
                    point["decision"] = "ineligible_min_accepted"
                    stop_reason = "n_below_25; sequence_stopped"
                else:
                    p_value = _binomial_lower_tail_pvalue(point["errors"], n_accepted)
                    point["p_value"] = p_value
                    point["decision"] = (
                        "rejected" if p_value <= COHORT_ALPHA else "not_rejected"
                    )
                    tested_thresholds.append(threshold)
                    if point["decision"] == "rejected":
                        certified_threshold = threshold
                    else:
                        stop_reason = "first_non_rejection; sequence_stopped"
            point.pop("accepted_mask")
            curve.append(point)

        results[str(cohort)] = {
            "status": "certified" if certified_threshold is not None else "not_certified",
            "certified_threshold": certified_threshold,
            "alpha_cohort": COHORT_ALPHA,
            "risk_limit": RISK_LIMIT,
            "minimum_accepted": MIN_ACCEPTED,
            "n_total": total,
            "tested_thresholds": tested_thresholds,
            "stop_reason": stop_reason or "all_thresholds_rejected",
            "curve": curve,
            "aurc": _aurc(curve),
            "aurc_interpretation": (
                "descriptive; unnormalised trapezoidal area over observed "
                "positive coverages only"
            ),
        }
    return {
        "partition": partition,
        "split": split,
        "thresholds": list(THRESHOLDS),
        "cohort_alpha": COHORT_ALPHA,
        "risk_limit": RISK_LIMIT,
        "results": results,
    }
