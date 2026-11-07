"""DEV-only threshold calibration and evaluation metrics for Phase 1b.

This module never loads datasets or runs models. TEST evaluation is fail-closed:
it requires a frozen threshold artifact produced from DEV and matching provenance.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

THRESHOLD_SCHEMA_VERSION = "phase1b-dev-thresholds-v1"
CALIBRATION_PROTOCOL = "phase1b-dev-calibration-v1"
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20261003
THRESHOLD_GRID = tuple(i / 100 for i in range(1, 100))


def _validate_rows(
    scores: Sequence[float],
    labels: Sequence[int],
    cohorts: Sequence[str],
) -> None:
    if not scores or len(scores) != len(labels) or len(scores) != len(cohorts):
        raise ValueError("scores, labels and cohorts must be non-empty and equally sized")
    for score in scores:
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("scores must be numeric")
        if not math.isfinite(float(score)) or not 0.0 <= float(score) <= 1.0:
            raise ValueError("scores must be finite and in [0, 1]")
    if any(label not in (0, 1) or isinstance(label, bool) for label in labels):
        raise ValueError("labels must be binary integers 0 or 1")
    if any(not isinstance(cohort, str) or not cohort for cohort in cohorts):
        raise ValueError("cohorts must be non-empty strings")


def _recalls(labels: Sequence[int], predictions: Sequence[int]) -> dict[str, float]:
    counts = Counter(labels)
    correct = Counter(
        label for label, pred in zip(labels, predictions, strict=True) if label == pred
    )
    if counts[0] == 0 or counts[1] == 0:
        raise ValueError("balanced accuracy requires both classes")
    return {"0": correct[0] / counts[0], "1": correct[1] / counts[1]}


def balanced_accuracy(labels: Sequence[int], predictions: Sequence[int]) -> float:
    recalls = _recalls(labels, predictions)
    return (recalls["0"] + recalls["1"]) / 2.0


def macro_f1(labels: Sequence[int], predictions: Sequence[int]) -> float:
    values: list[float] = []
    for class_label in (0, 1):
        tp = sum(
            y == class_label and p == class_label for y, p in zip(labels, predictions, strict=True)
        )
        fp = sum(
            y != class_label and p == class_label for y, p in zip(labels, predictions, strict=True)
        )
        fn = sum(
            y == class_label and p != class_label for y, p in zip(labels, predictions, strict=True)
        )
        denominator = 2 * tp + fp + fn
        values.append((2 * tp / denominator) if denominator else 0.0)
    return sum(values) / 2.0


def confusion_matrix_2x2(labels: Sequence[int], predictions: Sequence[int]) -> list[list[int]]:
    """Rows are true labels [0, 1], columns are predicted labels [0, 1]."""
    matrix = [[0, 0], [0, 0]]
    for label, prediction in zip(labels, predictions, strict=True):
        matrix[label][prediction] += 1
    return matrix


def _select_threshold(scores: Sequence[float], labels: Sequence[int]) -> float:
    if len(scores) != len(labels) or not scores:
        raise ValueError("threshold calibration requires equally sized non-empty DEV arrays")
    best_threshold: float | None = None
    best_ba = -1.0
    for threshold in THRESHOLD_GRID:
        predictions = [int(float(score) > threshold) for score in scores]
        value = balanced_accuracy(labels, predictions)
        # Grid is ascending: strict improvement preserves the smaller threshold on ties.
        if value > best_ba:
            best_ba = value
            best_threshold = threshold
    if best_threshold is None:
        raise ValueError("threshold calibration failed")
    return best_threshold


def calibrate_by_cohort(
    scores: Sequence[float],
    labels: Sequence[int],
    cohorts: Sequence[str],
) -> dict[str, float]:
    """Maximize DEV balanced accuracy independently per cohort; tie -> lower threshold."""
    _validate_rows(scores, labels, cohorts)
    indices: dict[str, list[int]] = defaultdict(list)
    for index, cohort in enumerate(cohorts):
        indices[cohort].append(index)
    return {
        cohort: _select_threshold(
            [float(scores[i]) for i in group],
            [labels[i] for i in group],
        )
        for cohort, group in sorted(indices.items())
    }


def make_frozen_threshold_artifact(
    *,
    model: str,
    manifest_sha256: str,
    thresholds: Mapping[str, float],
    mode: str = "dev_calibrated_by_cohort",
    protocol: str = CALIBRATION_PROTOCOL,
) -> dict[str, Any]:
    """Build versioned provenance metadata; callers persist it as immutable JSON."""
    if not model or not isinstance(model, str):
        raise ValueError("model identifier is required")
    if len(manifest_sha256) != 64 or any(c not in "0123456789abcdef" for c in manifest_sha256):
        raise ValueError("manifest_sha256 must be a lowercase SHA-256 hex digest")
    if mode not in {"fixed_0.5", "dev_calibrated_by_cohort"}:
        raise ValueError("unsupported threshold mode")
    if not thresholds:
        raise ValueError("thresholds must contain at least one cohort")
    normalized: dict[str, float] = {}
    for cohort, threshold in sorted(thresholds.items()):
        if not cohort or not isinstance(threshold, (int, float)) or not 0.01 <= threshold <= 0.99:
            raise ValueError("each cohort needs a threshold in [0.01, 0.99]")
        normalized[cohort] = float(threshold)
    if mode == "fixed_0.5" and any(value != 0.5 for value in normalized.values()):
        raise ValueError("fixed_0.5 artifact must contain only threshold 0.5")
    return {
        "schema_version": THRESHOLD_SCHEMA_VERSION,
        "frozen": True,
        "source_split": "dev",
        "mode": mode,
        "model": model,
        "protocol": protocol,
        "manifest_sha256": manifest_sha256,
        "thresholds_by_cohort": normalized,
    }


def _validate_frozen_artifact(
    artifact: Mapping[str, Any] | None,
    *,
    model: str | None,
    protocol: str | None,
    manifest_sha256: str | None,
) -> Mapping[str, Any]:
    if artifact is None:
        raise ValueError("TEST split requires a frozen DEV threshold artifact")
    if (
        artifact.get("schema_version") != THRESHOLD_SCHEMA_VERSION
        or artifact.get("frozen") is not True
        or artifact.get("source_split") != "dev"
    ):
        raise ValueError("threshold artifact is not a frozen DEV artifact")
    if model is None or artifact.get("model") != model:
        raise ValueError("threshold artifact model mismatch")
    if protocol is None or artifact.get("protocol") != protocol:
        raise ValueError("threshold artifact protocol mismatch")
    if manifest_sha256 is None or artifact.get("manifest_sha256") != manifest_sha256:
        raise ValueError("threshold artifact manifest mismatch")
    thresholds = artifact.get("thresholds_by_cohort")
    if not isinstance(thresholds, dict) or not thresholds:
        raise ValueError("threshold artifact has no cohort thresholds")
    return artifact


def predict_scores(
    scores: Sequence[float],
    cohorts: Sequence[str],
    *,
    mode: str,
    split: str,
    frozen_thresholds: Mapping[str, Any] | None = None,
    model: str | None = None,
    protocol: str | None = None,
    manifest_sha256: str | None = None,
) -> list[int]:
    """Predict labels; TEST can only consume a frozen, provenance-matched threshold file."""
    if len(scores) != len(cohorts) or not scores:
        raise ValueError("scores and cohorts must be non-empty and equally sized")
    if split not in {"dev", "test"}:
        raise ValueError("split must be dev or test")
    if mode not in {"fixed_0.5", "dev_calibrated_by_cohort"}:
        raise ValueError("unsupported threshold mode")
    if split == "test":
        artifact = _validate_frozen_artifact(
            frozen_thresholds,
            model=model,
            protocol=protocol,
            manifest_sha256=manifest_sha256,
        )
        if artifact.get("mode") != mode:
            raise ValueError("threshold artifact mode mismatch")
        threshold_map = artifact["thresholds_by_cohort"]
    elif mode == "fixed_0.5":
        threshold_map = {cohort: 0.5 for cohort in set(cohorts)}
    else:
        raise ValueError("DEV calibrated predictions require labels and calibrate_by_cohort()")
    if any(cohort not in threshold_map for cohort in cohorts):
        raise ValueError("threshold artifact is missing a requested cohort")
    for score in scores:
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError("scores must be numeric")
        if not math.isfinite(float(score)) or not 0.0 <= float(score) <= 1.0:
            raise ValueError("scores must be finite and in [0, 1]")
    return [
        int(float(score) > float(threshold_map[cohort]))
        for score, cohort in zip(scores, cohorts, strict=True)
    ]


def _ba_from_counts(tp: Any, fn: Any, tn: Any, fp: Any) -> Any:
    """Vectorised balanced accuracy from 2x2 counts; NaN where a class is absent."""
    import numpy as np

    pos = tp + fn
    neg = tn + fp
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where((pos > 0) & (neg > 0), (tp / pos + tn / neg) / 2.0, np.nan)


def _macro_f1_from_counts(tp: Any, fn: Any, tn: Any, fp: Any) -> Any:
    import numpy as np

    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = 2 * tp + fp + fn
        d0 = 2 * tn + fn + fp
        f1_pos = np.where(d1 > 0, 2 * tp / d1, 0.0)
        f1_neg = np.where(d0 > 0, 2 * tn / d0, 0.0)
    return (f1_pos + f1_neg) / 2.0


def _cell_codes(labels: Sequence[int], predictions: Sequence[int]) -> Any:
    """Encode each case as 0=TP, 1=FN, 2=TN, 3=FP."""
    import numpy as np

    y = np.asarray(labels, dtype=np.int8)
    p = np.asarray(predictions, dtype=np.int8)
    return np.where(y == 1, np.where(p == 1, 0, 1), np.where(p == 0, 2, 3))


def _resampled_counts(codes: Any, replicates: int, rng: Any) -> tuple[Any, Any, Any, Any]:
    """Case bootstrap without materialising an n x B index matrix (multinomial on cells)."""
    import numpy as np

    n = int(codes.shape[0])
    probabilities = np.bincount(codes, minlength=4) / n
    counts = rng.multinomial(n, probabilities, size=replicates).astype(np.float64)
    return counts[:, 0], counts[:, 1], counts[:, 2], counts[:, 3]


def _percentile_ci(values: Any, replicates: int) -> dict[str, Any]:
    import numpy as np

    finite = values[np.isfinite(values)]
    undefined = int(replicates - finite.shape[0])
    if finite.shape[0] == 0:
        return {
            "lower": None,
            "upper": None,
            "valid_replicates": 0,
            "undefined_replicates": undefined,
        }
    lower, upper = np.percentile(finite, [2.5, 97.5])
    return {
        "lower": float(lower),
        "upper": float(upper),
        "valid_replicates": int(finite.shape[0]),
        "undefined_replicates": undefined,
    }


def _bootstrap_ci(
    labels: Sequence[int],
    predictions: Sequence[int],
    *,
    metric: str,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Percentile CI for a case bootstrap, computed exactly via multinomial cell counts.

    Resampling n cases with replacement is equivalent in distribution to drawing the
    2x2 cell counts from Multinomial(n, observed cell proportions); this is O(B) instead
    of O(n * B), so 10,000 replicates on ~30k cases take milliseconds.
    """
    import numpy as np

    if replicates < 1:
        raise ValueError("bootstrap replicates must be positive")
    if metric not in {"balanced_accuracy", "macro_f1"}:
        raise ValueError("unsupported bootstrap metric")
    rng = np.random.default_rng(seed)
    tp, fn, tn, fp = _resampled_counts(_cell_codes(labels, predictions), replicates, rng)
    values = (
        _ba_from_counts(tp, fn, tn, fp)
        if metric == "balanced_accuracy"
        else _macro_f1_from_counts(tp, fn, tn, fp)
    )
    return _percentile_ci(values, replicates)


def _bootstrap_macro_dataset_ba_ci(
    labels: Sequence[int],
    predictions: Sequence[int],
    datasets: Sequence[str],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Stratified bootstrap of the leaderboard metric: resample within each dataset,
    recompute each dataset BA, then average across datasets (dataset set held fixed)."""
    import numpy as np

    rng = np.random.default_rng(seed)
    groups: dict[str, list[int]] = defaultdict(list)
    for index, dataset in enumerate(datasets):
        groups[dataset].append(index)
    per_dataset = []
    for _dataset, idx in sorted(groups.items()):
        codes = _cell_codes([labels[i] for i in idx], [predictions[i] for i in idx])
        tp, fn, tn, fp = _resampled_counts(codes, replicates, rng)
        per_dataset.append(_ba_from_counts(tp, fn, tn, fp))
    stacked = np.vstack(per_dataset)
    macro = np.where(np.isfinite(stacked).all(axis=0), stacked.mean(axis=0), np.nan)
    result = _percentile_ci(macro, replicates)
    result["method"] = "stratified_by_dataset_case_bootstrap"
    return result


def _summary(labels: Sequence[int], predictions: Sequence[int]) -> dict[str, Any]:
    recalls = _recalls(labels, predictions)
    return {
        "n": len(labels),
        "balanced_accuracy": (recalls["0"] + recalls["1"]) / 2.0,
        "macro_f1": macro_f1(labels, predictions),
        "confusion_matrix_2x2": confusion_matrix_2x2(labels, predictions),
        "recall_by_class": recalls,
    }


def evaluate_metrics(
    rows: Sequence[Mapping[str, Any]],
    predictions: Sequence[int],
    *,
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Compute metrics on supplied labels/predictions; this function does not run models."""
    if not rows or len(rows) != len(predictions):
        raise ValueError("rows and predictions must be non-empty and equally sized")
    labels: list[int] = []
    datasets: list[str] = []
    for row in rows:
        label = row.get("label")
        dataset = row.get("dataset")
        if (
            label not in (0, 1)
            or isinstance(label, bool)
            or not isinstance(dataset, str)
            or not dataset
        ):
            raise ValueError("rows require binary integer labels and a non-empty dataset")
        labels.append(label)
        datasets.append(dataset)
    if any(pred not in (0, 1) or isinstance(pred, bool) for pred in predictions):
        raise ValueError("predictions must be binary integers")
    overall = _summary(labels, predictions)

    groups: dict[str, list[int]] = defaultdict(list)
    for index, dataset in enumerate(datasets):
        groups[dataset].append(index)
    by_dataset = {
        dataset: _summary([labels[i] for i in idx], [predictions[i] for i in idx])
        for dataset, idx in sorted(groups.items())
    }
    macro_dataset_ba = sum(item["balanced_accuracy"] for item in by_dataset.values()) / len(
        by_dataset
    )

    ragtruth_mask = [str(dataset).lower() == "ragtruth" for dataset in datasets]
    subsets: dict[str, Any] = {}
    for name, keep in (
        ("all", [True] * len(rows)),
        ("without_ragtruth", [not flag for flag in ragtruth_mask]),
        ("ragtruth_only", ragtruth_mask),
    ):
        indices = [i for i, include in enumerate(keep) if include]
        if not indices:
            subsets[name] = {"n": 0, "status": "not_available"}
            continue
        try:
            subsets[name] = _summary(
                [labels[i] for i in indices], [predictions[i] for i in indices]
            )
        except ValueError:
            subsets[name] = {"n": len(indices), "status": "undefined_single_class"}

    # Bootstrap over individual cases for the overall metrics. Dataset macro BA is
    # reported separately as the leaderboard metric (mean of dataset BAs).
    overall["balanced_accuracy_ci95"] = _bootstrap_ci(
        labels,
        predictions,
        metric="balanced_accuracy",
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
    )
    overall["macro_f1_ci95"] = _bootstrap_ci(
        labels,
        predictions,
        metric="macro_f1",
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
    )
    macro_dataset_ci = _bootstrap_macro_dataset_ba_ci(
        labels,
        predictions,
        datasets,
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
    )
    return {
        "n": len(rows),
        "balanced_accuracy_global": overall["balanced_accuracy"],
        "balanced_accuracy_macro_dataset": macro_dataset_ba,
        "macro_f1_global": overall["macro_f1"],
        "confusion_matrix_2x2": overall["confusion_matrix_2x2"],
        "recall_by_class": overall["recall_by_class"],
        "by_dataset": by_dataset,
        "subsets": subsets,
        "bootstrap": {
            "replicates": bootstrap_replicates,
            "seed": bootstrap_seed,
            "global_balanced_accuracy_ci95": overall["balanced_accuracy_ci95"],
            "global_macro_f1_ci95": overall["macro_f1_ci95"],
            "macro_dataset_balanced_accuracy_ci95": macro_dataset_ci,
            "generator": "numpy.random.default_rng (PCG64)",
        },
    }
