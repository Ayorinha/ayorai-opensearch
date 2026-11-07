"""Pure-Python probabilistic metrics and adaptive reliability bins."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence

N_ECE_BINS = 15
PROBABILITY_CLIP = 1e-15


def _clip(probability: float) -> float:
    return min(1.0 - PROBABILITY_CLIP, max(PROBABILITY_CLIP, probability))


def _validate(
    probabilities: Sequence[float], labels: Sequence[int]
) -> tuple[list[float], list[int]]:
    if not probabilities or len(probabilities) != len(labels):
        raise ValueError("probabilities and labels must be non-empty and equally sized")
    probs: list[float] = []
    ys: list[int] = []
    for probability in probabilities:
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            raise ValueError("probabilities must be numeric")
        value = float(probability)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("probabilities must be finite and in [0, 1]")
        probs.append(value)
    for label in labels:
        if isinstance(label, bool) or label not in (0, 1):
            raise ValueError("labels must be binary integers 0 or 1")
        ys.append(label)
    return probs, ys


def _auroc(probabilities: Sequence[float], labels: Sequence[int]) -> float | None:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None
    ordered = sorted(zip(probabilities, labels, strict=True), key=lambda item: item[0])
    rank_sum = 0.0
    position = 1
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = (2 * position + (end - index) - 1) / 2.0
        rank_sum += average_rank * sum(label for _, label in ordered[index:end])
        position += end - index
        index = end
    u_statistic = rank_sum - positives * (positives + 1) / 2.0
    return u_statistic / (positives * negatives)


def _auprc(probabilities: Sequence[float], labels: Sequence[int]) -> float | None:
    positives = sum(labels)
    if positives == 0 or positives == len(labels):
        return None
    ordered = sorted(
        zip(probabilities, labels, strict=True), key=lambda item: item[0], reverse=True
    )
    true_positives = 0
    false_positives = 0
    previous_recall = 0.0
    average_precision = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        group = ordered[index:end]
        group_positives = sum(label for _, label in group)
        true_positives += group_positives
        false_positives += len(group) - group_positives
        recall = true_positives / positives
        precision = true_positives / (true_positives + false_positives)
        average_precision += (recall - previous_recall) * precision
        previous_recall = recall
        index = end
    return average_precision


def _adaptive_ece(
    probabilities: Sequence[float], labels: Sequence[int], n_bins: int
) -> tuple[float, int, list[dict[str, float | int]]]:
    grouped: dict[float, list[int]] = defaultdict(list)
    for probability, label in zip(probabilities, labels, strict=True):
        grouped[probability].append(label)

    bins: dict[int, list[tuple[float, int]]] = defaultdict(list)
    cumulative = 0
    total = len(probabilities)
    for probability in sorted(grouped):
        group = grouped[probability]
        bin_index = min(
            n_bins - 1, ((2 * cumulative + len(group)) * n_bins) // (2 * total)
        )
        bins[bin_index].extend((probability, label) for label in group)
        cumulative += len(group)

    reliability: list[dict[str, float | int]] = []
    weighted_error = 0.0
    for bin_index, members in sorted(bins.items()):
        count = len(members)
        confidence = sum(probability for probability, _ in members) / count
        observed = sum(label for _, label in members) / count
        weighted_error += count / total * abs(confidence - observed)
        reliability.append(
            {
                "bin": bin_index,
                "n": count,
                "mean_confidence": confidence,
                "observed_frequency": observed,
            }
        )
    return weighted_error, n_bins - len(bins), reliability


def probabilistic_metrics(
    probabilities: Sequence[float], labels: Sequence[int], *, n_bins: int = N_ECE_BINS
) -> dict[str, object]:
    """Compute AUROC, stepwise average precision, Brier, log-loss and adaptive ECE."""
    probs, ys = _validate(probabilities, labels)
    if n_bins < 1:
        raise ValueError("n_bins must be positive")

    prevalence = sum(ys) / len(ys)
    auroc = _auroc(probs, ys)
    auprc = _auprc(probs, ys)
    brier = sum(
        (probability - label) ** 2 for probability, label in zip(probs, ys, strict=True)
    ) / len(ys)
    log_loss = -sum(
        label * math.log(_clip(probability))
        + (1 - label) * math.log(_clip(1.0 - probability))
        for probability, label in zip(probs, ys, strict=True)
    ) / len(ys)
    ece, empty_bins, reliability = _adaptive_ece(probs, ys, n_bins)
    single_class = prevalence in (0.0, 1.0)
    return {
        "n": len(ys),
        "prevalence": prevalence,
        "auroc": auroc,
        "auprc": auprc,
        "auroc_auprc_status": "undefined_single_class" if single_class else "defined",
        "brier_score": brier,
        "log_loss": log_loss,
        "ece": ece,
        "ece_bins_requested": n_bins,
        "ece_bins_empty": empty_bins,
        "reliability_diagram": reliability,
    }
