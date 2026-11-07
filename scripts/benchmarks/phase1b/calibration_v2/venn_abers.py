"""NumPy reference implementation of inductive Venn-Abers calibration.

The reference follows Section 2 of Vovk, Petej, and Fedorova (NeurIPS 2015):
for each query score, fit isotonic regression twice after appending (s, 0)
and (s, 1). The log-minimax point probability follows Section 4:
p = p1 / (1 - p0 + p1).

Citation:
V. Vovk, I. Petej, and V. Fedorova, "Large-scale probabilistic predictors
with and without guarantees of validity," Advances in Neural Information
Processing Systems 28 (NIPS 2015), pp. 892-900.
https://doi.org/10.5555/2969239.2969339

This deliberately favors a transparent per-query reference over the paper's
optimized preprocessing algorithm; the paper points to a separate reference
for the detailed construction of its precomputed F0/F1 vectors.
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
