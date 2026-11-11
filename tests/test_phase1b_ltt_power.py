"""The LTT sample-size floors cited in the preregistrations are reproducible."""

from __future__ import annotations

import pytest

from scripts.benchmarks.phase1b.ltt_power import critical_errors, power, robust_floor


def test_critical_errors_respects_level() -> None:
    k = critical_errors(400, 0.10, 0.05 / 11)
    assert k >= 0
    # One more error would exceed the level.
    assert power(400, 0.10, 0.05 / 11, 0.10) <= 0.05 / 11 + 1e-12


@pytest.mark.parametrize(
    ("pairs", "p1", "expected"),
    [
        # Historical Calibration V2 family: 1 candidate x 11 cohorts.
        (11, 0.03, 168),
        (11, 0.05, 367),
        (11, 0.07, 1108),
        # Proposed stage-3 family: 2 candidates x 11 cohorts.
        (22, 0.03, 193),
        (22, 0.05, 420),
        (22, 0.07, 1258),
    ],
)
def test_reproduces_floors_up_to_horizon(pairs: int, p1: float, expected: int) -> None:
    assert robust_floor(0.10, 0.05 / pairs, p1, 0.80, horizon=2500) == expected



@pytest.mark.parametrize(
    ("r_max", "delta_pair", "p1", "target", "horizon"),
    [
        (0.0, 0.05, 0.03, 0.80, 100),
        (0.10, 0.0, 0.03, 0.80, 100),
        (0.10, 0.05, 0.10, 0.80, 100),
        (0.10, 0.05, 0.03, 1.0, 100),
        (0.10, 0.05, 0.03, 0.80, 0),
    ],
)
def test_rejects_invalid_planning_inputs(
    r_max: float, delta_pair: float, p1: float, target: float, horizon: int
) -> None:
    with pytest.raises(ValueError):
        robust_floor(r_max, delta_pair, p1, target, horizon)
