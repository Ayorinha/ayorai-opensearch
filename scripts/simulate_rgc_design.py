#!/usr/bin/env python3
"""Design simulation for the RGC benchmark (proposal; not a benchmark result).

Uses only synthetic random labels. No pilot or benchmark case is read, and
the AYORAI ATTRACTOR is not imported or executed.

Part 1 — inter-annotator agreement. Two simulated annotators label n cases
over the five RGC verdicts. Each annotator gives the true label with
probability ``acc`` and otherwise a uniformly random wrong label. For each
scenario the script reports the median Cohen's kappa, the median Gwet's AC1,
the median lower bound of a percentile bootstrap 95% CI for kappa, and how
often each reading of "kappa >= 0.6" (point estimate vs. CI lower bound)
would be met.

Part 2 — power of the preregistered primary criterion (H1). The baseline is
right exactly on gold == majority class (probability ``base``). The system is
right with probability ``system``, independently of the baseline (stated
assumption). H1 counts as supported only when all three preregistered
conditions hold: margin >= 10 pp, CI95 lower bound of system accuracy above
baseline accuracy, and two-sided exact McNemar p < 0.05.

Run: ``python scripts/simulate_rgc_design.py`` (about three minutes).
"""

from __future__ import annotations

import sys
from math import comb
from random import Random

K = 5
SEED = 20261003


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


def mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2**n)


def power(rng: Random, reps: int = 2000, boots: int = 1000) -> None:
    print("\n  n  base  system  P(H1 supported)")
    for n in (90, 210, 300):
        for base, system in ((0.40, 0.50), (0.40, 0.55), (0.40, 0.60), (0.40, 0.70)):
            wins = 0
            for _ in range(reps):
                g = [rng.random() < base for _ in range(n)]
                s = [rng.random() < system for _ in range(n)]
                acc_s, acc_b = sum(s) / n, sum(g) / n
                draws = sorted(
                    sum(rng.random() < acc_s for _ in range(n)) / n for _ in range(boots // 10)
                )
                low = draws[int(0.025 * (len(draws) - 1))]
                b = sum(x and not y for x, y in zip(s, g, strict=True))
                c = sum(y and not x for x, y in zip(s, g, strict=True))
                if acc_s - acc_b >= 0.10 - 1e-12 and low > acc_b and mcnemar_p(b, c) < 0.05:
                    wins += 1
            print(f"{n:4d}  {base:.2f}  {system:.2f}    {wins / reps:.2f}")


def main() -> int:
    rng = Random(SEED)  # nosec B311 - deterministic design simulation
    agreement(rng)
    power(rng)
    return 0


if __name__ == "__main__":
    sys.exit(main())
