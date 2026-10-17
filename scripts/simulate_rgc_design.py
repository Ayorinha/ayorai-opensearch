#!/usr/bin/env python3
"""RGC design simulation using synthetic labels; not a benchmark result.

Part 1 simulates inter-annotator agreement over five classes.
Part 2 simulates H1 with the same paired-case bootstrap and exact McNemar
implementation used by evals/ptbr/rgc_eval.py. The baseline is a constant
prediction of the majority reference class in each simulated evaluation
partition (ties follow the declared class order), not an independent Bernoulli
coin. System correctness is simulated under two dependence assumptions:
independent correctness indicators, and a target positive phi correlation of
0.5 with baseline correctness. The joint probability is clipped to its
mathematically feasible bounds, so the achieved correlation may be below 0.5.

Only synthetic labels are generated. No pilot or benchmark case is read and
the AYORAI ATTRACTOR Judge is not executed.

Run from an installed project environment:
    python scripts/simulate_rgc_design.py
"""

from __future__ import annotations

import sys
from array import array
from collections import Counter
from math import sqrt
from random import Random

from ayorai_attractor.evaluation.stats import bootstrap_accuracy, mcnemar_exact_pvalue

try:
    import numpy as np
except ImportError:  # optional acceleration; the evaluator's pure-Python bootstrap is the fallback
    np = None

K = 5
LABELS = tuple(f"C{i}" for i in range(K))
SEED = 20261003
BOOTSTRAPS = 10_000
POWER_REPETITIONS = 200
POSITIVE_PHI_TARGET = 0.5


def kappa(a: list[int], b: list[int]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pe = sum((a.count(k) / n) * (b.count(k) / n) for k in range(K))
    return (po - pe) / (1 - pe)


def ac1(a: list[int], b: list[int]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    pi = [(a.count(k) + b.count(k)) / (2 * n) for k in range(K)]
    pe = sum(p * (1 - p) for p in pi) / (K - 1)
    return (po - pe) / (1 - pe)


def annotate(rng: Random, truth: list[int], acc: float) -> list[int]:
    return [t if rng.random() < acc else (t + rng.randrange(1, K)) % K for t in truth]


def median(values: list[float]) -> float:
    s = sorted(values)
    return s[len(s) // 2]


def agreement(rng: Random, reps: int = 200, boots: int = 400) -> None:
    scenarios = {
        "balanced": [0.2] * 5,
        "imbalanced": [0.40, 0.30, 0.15, 0.10, 0.05],
        "very_imbalanced": [0.55, 0.25, 0.10, 0.06, 0.04],
    }
    print("scenario         acc   n  kappa_med AC1_med ci_low_med P(k>=.6) P(ci_low>=.6)")
    for name, prevalence in scenarios.items():
        for acc in (0.80, 0.85, 0.90):
            for n in (100, 300):
                ks, acs, lows = [], [], []
                for _ in range(reps):
                    truth = rng.choices(range(K), weights=prevalence, k=n)
                    a, b = annotate(rng, truth, acc), annotate(rng, truth, acc)
                    ks.append(kappa(a, b))
                    acs.append(ac1(a, b))
                    boot = []
                    for _ in range(boots):
                        idx = [rng.randrange(n) for _ in range(n)]
                        boot.append(kappa([a[i] for i in idx], [b[i] for i in idx]))
                    boot.sort()
                    lows.append(boot[int(0.025 * (boots - 1))])
                print(
                    f"{name:15s} {acc:.2f} {n:4d}  {median(ks):.3f}    {median(acs):.3f}"
                    f"   {median(lows):.3f}      {sum(k >= 0.6 for k in ks) / reps:.2f}"
                    f"     {sum(lo >= 0.6 for lo in lows) / reps:.2f}"
                )


def _bootstrap_indices(n: int) -> object | None:
    """Precompute the executor's exact 10,000 seeded paired-case resamples."""
    if np is None:
        return None
    rng = Random(SEED)
    raw = array("H")
    for _ in range(BOOTSTRAPS):
        for _ in range(n):
            raw.append(rng.randrange(n))
    return np.frombuffer(raw, dtype=np.uint16).reshape(BOOTSTRAPS, n)


def _accuracy_ci_lower(
    gold: list[str], predicted: list[str], indices: object | None
) -> float:
    if indices is None:
        return bootstrap_accuracy(
            gold, predicted, iterations=BOOTSTRAPS, seed=SEED
        )[0]
    outcomes = np.asarray(
        [actual == guess for actual, guess in zip(gold, predicted, strict=True)],
        dtype=np.bool_,
    )
    samples = outcomes[indices].mean(axis=1)
    samples.sort()
    return float(samples[int(0.025 * (BOOTSTRAPS - 1))])


def _majority_label(gold: list[str]) -> str:
    counts = Counter(gold)
    return min(counts, key=lambda label: (-counts[label], LABELS.index(label)))


def _system_predictions(
    rng: Random,
    gold: list[str],
    system_accuracy: float,
    phi_target: float,
) -> list[str]:
    """Generate labels with target accuracy and specified dependence on baseline correctness."""
    majority = _majority_label(gold)
    baseline_correct = [label == majority for label in gold]
    p_base = sum(baseline_correct) / len(gold)
    p_system = system_accuracy

    # Joint probability P(system correct AND baseline correct) for target phi.
    lower = max(0.0, p_system + p_base - 1.0)
    upper = min(p_system, p_base)
    joint = p_system * p_base + phi_target * sqrt(
        max(0.0, p_system * (1.0 - p_system) * p_base * (1.0 - p_base))
    )
    joint = min(upper, max(lower, joint))

    if p_base <= 0.0:
        p_system_given_base = 0.0
        p_system_given_baseline_wrong = p_system
    elif p_base >= 1.0:
        p_system_given_base = p_system
        p_system_given_baseline_wrong = 0.0
    else:
        p_system_given_base = joint / p_base
        p_system_given_baseline_wrong = (p_system - joint) / (1.0 - p_base)

    predicted: list[str] = []
    for actual, baseline_ok in zip(gold, baseline_correct, strict=True):
        conditional = (
            p_system_given_base if baseline_ok else p_system_given_baseline_wrong
        )
        if rng.random() < conditional:
            predicted.append(actual)
        else:
            actual_index = LABELS.index(actual)
            predicted.append(LABELS[(actual_index + rng.randrange(1, K)) % K])
    return predicted


def power(rng: Random) -> None:
    prevalences = {
        "balanced": [0.20, 0.20, 0.20, 0.20, 0.20],
        "imbalanced": [0.40, 0.30, 0.15, 0.10, 0.05],
        "very_imbalanced": [0.55, 0.25, 0.10, 0.06, 0.04],
    }
    print(
        "\nprevalence       n  system_acc  P(H1 independent)  "
        "P(H1 positive_phi_target_0.5)"
    )
    for scenario_index, (name, prevalence) in enumerate(prevalences.items()):
        scenario_rng = Random(SEED + scenario_index)
        for n in (90, 300):
            indices = _bootstrap_indices(n)
            for system_accuracy in (0.50, 0.55, 0.60, 0.70):
                probabilities = []
                for phi in (0.0, POSITIVE_PHI_TARGET):
                    supported = 0
                    for _ in range(POWER_REPETITIONS):
                        gold = scenario_rng.choices(LABELS, weights=prevalence, k=n)
                        baseline_label = _majority_label(gold)
                        baseline = [baseline_label] * n
                        predicted = _system_predictions(
                            scenario_rng, gold, system_accuracy, phi
                        )
                        accuracy = sum(
                            actual == guess
                            for actual, guess in zip(gold, predicted, strict=True)
                        ) / n
                        baseline_accuracy = sum(
                            actual == guess
                            for actual, guess in zip(gold, baseline, strict=True)
                        ) / n
                        margin = accuracy - baseline_accuracy
                        ci_lower = _accuracy_ci_lower(gold, predicted, indices)
                        p_value = mcnemar_exact_pvalue(gold, predicted, baseline)
                        if (
                            margin >= 0.10 - 1e-12
                            and ci_lower > baseline_accuracy
                            and p_value < 0.05
                        ):
                            supported += 1
                    probabilities.append(supported / POWER_REPETITIONS)
                print(
                    f"{name:15s} {n:3d} {system_accuracy:10.2f} "
                    f"{probabilities[0]:18.3f} {probabilities[1]:27.3f}"
                )


def main() -> int:
    rng = Random(SEED)  # nosec B311 - synthetic simulation only, not cryptography
    agreement(rng)
    power(rng)
    return 0


if __name__ == "__main__":
    sys.exit(main())
