#!/usr/bin/env python3
"""Reproducible sample-size floors for the LTT risk certification (planning only).

Test, per (candidate, cohort) and threshold: H0: risk >= R_max against H1: risk < R_max,
with the exact one-sided binomial test at level delta_pair on the n accepted cases
(assumed independent; see the one-claim-per-document rule). The null is rejected when
the number of errors k satisfies P(Bin(n, R_max) <= k) <= delta_pair.

Power at a true error rate p1 is P(Bin(n, p1) <= k_crit(n)). Because the binomial is
discrete, power is not monotone in n; the *robust floor up to the horizon H* is the
smallest n such that power >= target for every n' in [n, H]. This is a numerical check
up to H, not a proof for every n' beyond H.

The number of pairs is the multiplicity family (candidates x cohorts); always state it.

These numbers are planning aids, not acceptance rules.
"""

from __future__ import annotations

import argparse
import json
import math


def _require_probability(name: str, value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0.0 < value < 1.0
    ):
        raise ValueError(f"{name} must be finite and strictly between 0 and 1")


def _pmf_row(n: int, p: float) -> list[float]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative integer")
    _require_probability("p", p)
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

    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    _require_probability("r_max", r_max)
    _require_probability("delta_pair", delta_pair)
    cumulative = 0.0
    k = -1
    for i, mass in enumerate(_pmf_row(n, r_max)):
        cumulative += mass
        if cumulative > delta_pair:
            break
        k = i
    return k


def power(n: int, r_max: float, delta_pair: float, p1: float) -> float:
    _require_probability("p1", p1)
    k = critical_errors(n, r_max, delta_pair)
    return sum(_pmf_row(n, p1)[: k + 1]) if k >= 0 else 0.0


def robust_floor(
    r_max: float, delta_pair: float, p1: float, target: float, horizon: int = 3000
) -> int:
    _require_probability("r_max", r_max)
    _require_probability("delta_pair", delta_pair)
    _require_probability("p1", p1)
    _require_probability("target", target)
    if p1 >= r_max:
        raise ValueError("p1 must be lower than r_max for the planned alternative")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
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
    _require_probability("r_max", args.r_max)
    _require_probability("delta_family", args.delta_family)
    if args.pairs < 1:
        parser.error("--pairs must be a positive integer")
    if args.horizon < 1:
        parser.error("--horizon must be a positive integer")
    _require_probability("power", args.power)
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
