"""Exact IVAP for E3 nested cross-fitting, with persistent PAVA stacks.

E3 needs about five times more Venn-Abers fits than Calibration V2 (nested cross-fitting
for every member), which the per-query reference in ``calibration_v2/venn_abers.py``
cannot do within the protected job's time limit. This module computes the same
quantities — the isotonic fit at the query after appending ``(s, 0)`` and ``(s, 1)`` —
without refitting PAVA from scratch for each query:

- the calibration scores are pooled by unique value, exactly as in the reference;
- one left-to-right PAVA pass keeps, for every prefix of groups, the top of a persistent
  block stack; one right-to-left pass does the same for every suffix;
- for a query, only the block that contains it can violate monotonicity, so the fit is
  obtained by merging that block with the adjacent prefix/suffix blocks until it is
  ordered.

Blocks of the isotonic fit of a prefix (or suffix) are unions inside the blocks of the fit
of the whole sequence, and the isotonic fit is unique, so the result equals the
reference up to floating-point summation order. Tests compare both on random and tied
data. Calibration V2 itself keeps using the reference implementation unchanged.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class _Stacks:
    """Persistent PAVA stacks over pooled calibration groups."""

    def __init__(self, weights: Sequence[float], sums: Sequence[float]) -> None:
        self.weight: list[float] = []
        self.total: list[float] = []
        self.parent: list[int] = []
        groups = len(weights)

        self.left_top = [-1] * (groups + 1)
        top = -1
        for group in range(groups):
            weight, total = float(weights[group]), float(sums[group])
            while top != -1 and self.total[top] / self.weight[top] > total / weight:
                weight += self.weight[top]
                total += self.total[top]
                top = self.parent[top]
            top = self._node(weight, total, top)
            self.left_top[group + 1] = top

        self.right_top = [-1] * (groups + 1)
        top = -1
        for group in range(groups - 1, -1, -1):
            weight, total = float(weights[group]), float(sums[group])
            while top != -1 and total / weight > self.total[top] / self.weight[top]:
                weight += self.weight[top]
                total += self.total[top]
                top = self.parent[top]
            top = self._node(weight, total, top)
            self.right_top[group] = top

    def _node(self, weight: float, total: float, parent: int) -> int:
        self.weight.append(weight)
        self.total.append(total)
        self.parent.append(parent)
        return len(self.weight) - 1

    def fit(self, weight: float, total: float, left: int, right: int) -> float:
        while True:
            if left != -1 and self.total[left] / self.weight[left] > total / weight:
                weight += self.weight[left]
                total += self.total[left]
                left = self.parent[left]
            elif right != -1 and total / weight > self.total[right] / self.weight[right]:
                weight += self.weight[right]
                total += self.total[right]
                right = self.parent[right]
            else:
                return total / weight


def ivap(
    calibration_scores: Sequence[float],
    calibration_labels: Sequence[int],
    query_scores: Sequence[float],
) -> dict[str, Any]:
    """Return IVAP p0, p1 and log-minimax p for each query (same contract as the reference)."""

    import numpy as np

    from scripts.benchmarks.phase1b.calibration_v2.venn_abers import _validated_arrays

    scores, labels, queries = _validated_arrays(
        calibration_scores, calibration_labels, query_scores
    )
    unique_scores, inverse = np.unique(scores, return_inverse=True)
    weights = np.bincount(inverse).astype(np.float64)
    sums = np.bincount(inverse, weights=labels).astype(np.float64)
    stacks = _Stacks(weights.tolist(), sums.tolist())
    groups = unique_scores.size

    positions = np.searchsorted(unique_scores, queries, side="left")
    p0 = np.empty(queries.size, dtype=np.float64)
    p1 = np.empty(queries.size, dtype=np.float64)
    for index, (query, position) in enumerate(
        zip(queries.tolist(), positions.tolist(), strict=True)
    ):
        tied = position < groups and unique_scores[position] == query
        if tied:
            base_weight, base_total = weights[position] + 1.0, float(sums[position])
            left, right = stacks.left_top[position], stacks.right_top[position + 1]
        else:
            base_weight, base_total = 1.0, 0.0
            left, right = stacks.left_top[position], stacks.right_top[position]
        p0[index] = stacks.fit(float(base_weight), base_total, left, right)
        p1[index] = stacks.fit(float(base_weight), base_total + 1.0, left, right)

    if np.any(p0 > p1):
        raise ArithmeticError("Venn-Abers interval invariant violated: p0 must be <= p1")
    return {"p0": p0, "p1": p1, "p": p1 / (1.0 - p0 + p1)}


def nested_ivap(
    scores: Sequence[float],
    labels: Sequence[int],
    folds: Sequence[int],
) -> tuple[dict[int, Any], Any]:
    """Nested cross-fitted IVAP probabilities without information from the outer fold.

    Returns ``(inner, outer)``:
    - ``inner[k][i]`` for ``fold[i] != k``: probability from a calibrator fitted on the
      folds other than ``k`` and ``fold[i]`` (``NaN`` on fold ``k``); used only to choose
      thresholds for outer fold ``k``;
    - ``outer[i]``: probability from a calibrator fitted on every fold except ``fold[i]``;
      used only to evaluate record ``i``.
    """

    import numpy as np

    score_array = np.asarray(scores, dtype=np.float64)
    label_array = np.asarray(labels, dtype=np.int64)
    fold_array = np.asarray(folds, dtype=np.int64)
    fold_ids = sorted(int(fold) for fold in np.unique(fold_array))
    if len(fold_ids) < 3:
        raise ValueError("nested cross-fitting requires at least three folds")

    outer = np.full(score_array.size, np.nan, dtype=np.float64)
    inner: dict[int, Any] = {}
    for outer_fold in fold_ids:
        held = fold_array == outer_fold
        outer[held] = ivap(score_array[~held], label_array[~held], score_array[held])["p"]
        values = np.full(score_array.size, np.nan, dtype=np.float64)
        for inner_fold in fold_ids:
            if inner_fold == outer_fold:
                continue
            query = fold_array == inner_fold
            calibration = ~query & ~held
            values[query] = ivap(
                score_array[calibration], label_array[calibration], score_array[query]
            )["p"]
        inner[outer_fold] = values
    if np.isnan(outer).any():
        raise ArithmeticError("nested cross-fit did not produce an outer prediction for every case")
    return inner, outer
