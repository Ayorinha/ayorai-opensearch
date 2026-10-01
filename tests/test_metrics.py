from ayorai_attractor.metrics import CostSample, mean


def test_cost_estimate_is_deterministic() -> None:
    sample = CostSample(1000, 500, 0.002, 0.004)
    assert sample.estimated_cost == 0.004


def test_mean() -> None:
    assert mean([1.0, 2.0, 3.0]) == 2.0
