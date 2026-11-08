#!/usr/bin/env python3
"""Reproducible sample-size floors for the LTT risk certification (planning only).

Test, per (candidate, cohort) and threshold: H0: risk >= R_max against H1: risk < R_max,
with the exact one-sided binomial test at level delta_pair on the n accepted cases
(assumed independent; see the one-claim-per-document rule). The null is rejected when
the number of errors k satisfies P(Bin(n, R_max) <= k) <= delta_pair.

Power at a true error rate p1 is P(Bin(n, p1) <= k_crit(n)). Because the binomial is
discrete, power is not monotone in n; the *robust floor* is the smallest n such that
power >= target for every n' >= n (checked up to ``horizon``).

These numbers are planning aids, not acceptance rules.
"""

from __future__ import annotations

import argparse
import json
import math


def _pmf_row(n: int, p: float) -> list[float]:
    log_p, log_q = math.log(p), math.log1p(-p)
    return [
        math.exp(
            math.lgamma(n + 1)
            - math.lgamma(i + 1)
            - math.lgamma(n - i + 1)
            + i * log_p
            + (n - i) * log_q
        )
        for i in range(n + 1)
    ]


def critical_errors(n: int, r_max: float, delta_pair: float) -> int:
    """Largest k with P(Bin(n, r_max) <= k) <= delta_pair; -1 if none."""

    cumulative = 0.0
    k = -1
    for i, mass in enumerate(_pmf_row(n, r_max)):
        cumulative += mass
        if cumulative > delta_pair:
            break
        k = i
    return k


def power(n: int, r_max: float, delta_pair: float, p1: float) -> float:
    k = critical_errors(n, r_max, delta_pair)
    return sum(_pmf_row(n, p1)[: k + 1]) if k >= 0 else 0.0


def robust_floor(
    r_max: float, delta_pair: float, p1: float, target: float, horizon: int = 3000
) -> int:
    last_failure = 0
    for n in range(1, horizon + 1):
        if power(n, r_max, delta_pair, p1) < target:
            last_failure = n
    if last_failure >= horizon:
        raise ValueError("horizon too small for this scenario")
    return last_failure + 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--r-max", type=float, required=True)
    parser.add_argument("--delta-family", type=float, required=True)
    parser.add_argument("--pairs", type=int, required=True, help="cohorts x candidates")
    parser.add_argument("--p1", type=float, nargs="+", required=True)
    parser.add_argument("--power", type=float, default=0.8)
    parser.add_argument("--horizon", type=int, default=3000)
    args = parser.parse_args()
    delta_pair = args.delta_family / args.pairs
    floors = {
        str(p1): robust_floor(args.r_max, delta_pair, p1, args.power, args.horizon)
        for p1 in args.p1
    }
    print(
        json.dumps(
            {
                "r_max": args.r_max,
                "delta_pair": delta_pair,
                "power": args.power,
                "robust_floors": floors,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
