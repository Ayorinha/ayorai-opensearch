"""The LTT sample-size floors cited in the preregistrations are reproducible."""

from __future__ import annotations

import pytest

from scripts.benchmarks.phase1b.ltt_power import critical_errors, power, robust_floor


def test_critical_errors_respects_level() -> None:
    k = critical_errors(400, 0.10, 0.05 / 11)
    assert k >= 0
    # One more error would exceed the level.
    assert power(400, 0.10, 0.05 / 11, 0.10) <= 0.05 / 11 + 1e-12


@pytest.mark.parametrize(("p1", "expected"), [(0.03, 168), (0.05, 367), (0.07, 1108)])
def test_reproduces_project_floors(p1: float, expected: int) -> None:
    assert robust_floor(0.10, 0.05 / 11, p1, 0.80, horizon=1800) == expected
