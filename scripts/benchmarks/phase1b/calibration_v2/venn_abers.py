"""NumPy reference implementation of inductive Venn-Abers calibration.

The reference follows Section 2 of Vovk, Petej, and Fedorova (NeurIPS 2015):
for each query score, fit isotonic regression twice after appending (s, 0)
and (s, 1). The log-minimax point probability follows Section 4:
p = p1 / (1 - p0 + p1).

This transparent NumPy/PAVA reference is the official implementation for
Calibration V2-2. No optimized/fast algorithm is implemented or implied:
auditability and agreement with the reference definition take precedence over
runtime optimization. Each query is evaluated independently from the same
calibration sample; the query's hypothetical label is appended only inside
its own fit.

Reference:
V. Vovk, I. Petej, and V. Fedorova, "Large-scale probabilistic predictors
with and without guarantees of validity," Advances in Neural Information
Processing Systems 28 (NeurIPS 2015), pp. 892-900.
https://proceedings.neurips.cc/paper/2015/hash/a9a1d5317a33ae8cef33961c34144f84-Abstract.html
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def _validated_arrays(
    calibration_scores: Sequence[float],
    calibration_labels: Sequence[int],
    query_scores: Sequence[float],
) -> tuple[Any, Any, Any]:
    import numpy as np

    scores = np.asarray(calibration_scores, dtype=np.float64)
    labels_raw = np.asarray(calibration_labels)
    queries = np.asarray(query_scores, dtype=np.float64)
    if scores.ndim != 1 or labels_raw.ndim != 1 or queries.ndim != 1:
        raise ValueError("scores, labels and query_scores must be one-dimensional")
    if scores.size == 0 or scores.size != labels_raw.size or queries.size == 0:
        raise ValueError("calibration arrays must be non-empty and equally sized")
    if not np.isfinite(scores).all() or not np.isfinite(queries).all():
        raise ValueError("scores must be finite")
    if labels_raw.dtype.kind not in "iu" or not np.isin(labels_raw, (0, 1)).all():
        raise ValueError("calibration_labels must contain binary integers 0 or 1")
    return scores, labels_raw.astype(np.float64), queries


def _pava_value(
    calibration_scores: Any,
    calibration_labels: Any,
    query_score: float,
    pseudo_label: int,
) -> float:
    """Return the fitted isotonic value at query_score using weighted PAVA."""
    import numpy as np

    scores = np.concatenate((calibration_scores, np.asarray([query_score])))
    labels = np.concatenate((calibration_labels, np.asarray([float(pseudo_label)])))

    unique_scores, inverse = np.unique(scores, return_inverse=True)
    weights = np.bincount(inverse).astype(np.float64)
    label_sums = np.bincount(inverse, weights=labels).astype(np.float64)

    # Each stack entry is [first index, exclusive end, total weight, label sum].
    blocks: list[list[float | int]] = []
    for index, (weight, label_sum) in enumerate(zip(weights, label_sums, strict=True)):
        blocks.append([index, index + 1, float(weight), float(label_sum)])
        while len(blocks) >= 2:
            left = blocks[-2]
            right = blocks[-1]
            left_mean = float(left[3]) / float(left[2])
            right_mean = float(right[3]) / float(right[2])
            if left_mean <= right_mean:
                break
            blocks.pop()
            blocks.pop()
            blocks.append(
                [
                    int(left[0]),
                    int(right[1]),
                    float(left[2]) + float(right[2]),
                    float(left[3]) + float(right[3]),
                ]
            )

    fitted = np.empty(unique_scores.size, dtype=np.float64)
    for start, end, weight, label_sum in blocks:
        fitted[int(start) : int(end)] = float(label_sum) / float(weight)

    query_index = int(np.searchsorted(unique_scores, query_score))
    return float(fitted[query_index])


def venn_abers_reference(
    calibration_scores: Sequence[float],
    calibration_labels: Sequence[int],
    query_scores: Sequence[float],
) -> dict[str, Any]:
    """Compute reference IVAP intervals and log-minimax probabilities.

    Duplicate calibration scores are pooled by their mean label before PAVA.
    A query tied with a calibration score is included as an additional weighted
    observation at that same score. Query scores may lie outside the calibration
    score range; no clipping or extrapolation rule is applied to the score axis.

    Returns NumPy arrays p0, p1 and p in query order.
    """
    import numpy as np

    scores, labels, queries = _validated_arrays(
        calibration_scores, calibration_labels, query_scores
    )
    p0 = np.empty(queries.size, dtype=np.float64)
    p1 = np.empty(queries.size, dtype=np.float64)

    for index, query_score in enumerate(queries):
        p0[index] = _pava_value(scores, labels, float(query_score), 0)
        p1[index] = _pava_value(scores, labels, float(query_score), 1)

    if np.any(p0 > p1):
        raise ArithmeticError("Venn-Abers interval invariant violated: p0 must be <= p1")

    denominator = 1.0 - p0 + p1
    probabilities = p1 / denominator
    return {"p0": p0, "p1": p1, "p": probabilities}


def _validated_crossfit_inputs(
    scores: Sequence[float],
    labels: Sequence[int],
    folds: Sequence[int],
) -> tuple[Any, Any, Any]:
    import numpy as np

    score_array = np.asarray(scores, dtype=np.float64)
    label_array = np.asarray(labels)
    fold_array = np.asarray(folds)
    if score_array.ndim != 1 or label_array.ndim != 1 or fold_array.ndim != 1:
        raise ValueError("scores, labels and folds must be one-dimensional")
    if score_array.size == 0 or score_array.size != label_array.size:
        raise ValueError("scores and labels must be non-empty and equally sized")
    if score_array.size != fold_array.size:
        raise ValueError("folds must have the same length as scores")
    if not np.isfinite(score_array).all():
        raise ValueError("scores must be finite")
    if label_array.dtype.kind not in "iu" or not np.isin(label_array, (0, 1)).all():
        raise ValueError("labels must contain binary integers 0 or 1")
    if fold_array.dtype.kind not in "iu" or np.any(fold_array < 0):
        raise ValueError("folds must contain non-negative integers")
    if np.unique(fold_array).size < 2:
        raise ValueError("cross-fitting requires at least two distinct folds")
    return score_array, label_array.astype(np.int8), fold_array.astype(np.int64)


def ivap_crossfit(
    scores: Sequence[float],
    labels: Sequence[int],
    folds: Sequence[int],
) -> dict[str, Any]:
    """Return IVAP p0, p1 and p as out-of-fold predictions.

    For each fold, the calibrator is fitted only on all other folds. The
    held-out fold's scores are queries; its labels are never passed to the
    calibrator. Fold identifiers are the deterministic assignments produced
    by the V2-1 crossfit_folds function.
    """
    import numpy as np

    score_array, label_array, fold_array = _validated_crossfit_inputs(scores, labels, folds)
    p0 = np.full(score_array.size, np.nan, dtype=np.float64)
    p1 = np.full(score_array.size, np.nan, dtype=np.float64)
    probabilities = np.full(score_array.size, np.nan, dtype=np.float64)

    for fold in np.unique(fold_array):
        held_out = fold_array == fold
        calibration = ~held_out
        if not np.any(calibration):
            raise ValueError(f"fold {int(fold)} has no calibration observations")
        result = venn_abers_reference(
            score_array[calibration],
            label_array[calibration],
            score_array[held_out],
        )
        p0[held_out] = result["p0"]
        p1[held_out] = result["p1"]
        probabilities[held_out] = result["p"]

    if np.isnan(p0).any() or np.isnan(p1).any() or np.isnan(probabilities).any():
        raise ArithmeticError("cross-fit did not produce predictions for every case")
    return {"p0": p0, "p1": p1, "p": probabilities}


def ivap_crossfit_mondrian(
    scores: Sequence[float],
    labels: Sequence[int],
    folds: Sequence[int],
    cohorts: Sequence[str],
    min_calibration: int = 200,
) -> dict[str, Any]:
    """Return per-cohort Mondrian IVAP predictions with explicit eligibility.

    Each fold is calibrated only with other-fold observations from the same
    cohort. A cohort is eligible only if every fold has at least
    min_calibration same-cohort calibration observations. Ineligible cohorts
    receive NaN predictions and status mondrian_unavailable; there is
    deliberately no pooled or global fallback.
    """
    import numpy as np

    score_array, label_array, fold_array = _validated_crossfit_inputs(scores, labels, folds)
    cohort_array = np.asarray(cohorts)
    if cohort_array.ndim != 1 or cohort_array.size != score_array.size:
        raise ValueError("cohorts must have the same length as scores")
    if cohort_array.dtype.kind not in "US" or any(
        not isinstance(value, str) or not value for value in cohorts
    ):
        raise ValueError("cohorts must contain non-empty strings")
    if isinstance(min_calibration, bool) or not isinstance(min_calibration, int):
        raise ValueError("min_calibration must be a positive integer")
    if min_calibration < 1:
        raise ValueError("min_calibration must be a positive integer")

    p0 = np.full(score_array.size, np.nan, dtype=np.float64)
    p1 = np.full(score_array.size, np.nan, dtype=np.float64)
    probabilities = np.full(score_array.size, np.nan, dtype=np.float64)
    row_status = np.full(score_array.size, "mondrian_unavailable", dtype=object)
    cohort_status: dict[str, dict[str, Any]] = {}

    for cohort in sorted(set(cohort_array.tolist())):
        cohort_mask = cohort_array == cohort
        cohort_folds = np.unique(fold_array[cohort_mask])
        calibration_counts = {
            int(fold): int(np.count_nonzero(cohort_mask & (fold_array != fold)))
            for fold in cohort_folds
        }
        minimum_count = min(calibration_counts.values())
        if minimum_count < min_calibration:
            cohort_status[str(cohort)] = {
                "status": "mondrian_unavailable",
                "minimum_calibration_n": minimum_count,
                "required_calibration_n": min_calibration,
            }
            continue

        cohort_status[str(cohort)] = {
            "status": "available",
            "minimum_calibration_n": minimum_count,
            "required_calibration_n": min_calibration,
        }
        for fold in cohort_folds:
            held_out = cohort_mask & (fold_array == fold)
            calibration = cohort_mask & (fold_array != fold)
            result = venn_abers_reference(
                score_array[calibration],
                label_array[calibration],
                score_array[held_out],
            )
            p0[held_out] = result["p0"]
            p1[held_out] = result["p1"]
            probabilities[held_out] = result["p"]
            row_status[held_out] = "available"

    return {
        "p0": p0,
        "p1": p1,
        "p": probabilities,
        "status": row_status,
        "cohort_status": cohort_status,
    }
