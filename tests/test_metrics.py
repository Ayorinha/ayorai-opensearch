from ayorai_attractor.metrics import (
    CostSample,
    MetricsCollector,
    mean,
    percentile,
)


def test_cost_estimate_is_deterministic() -> None:
    sample = CostSample(1000, 500, 0.002, 0.004)
    assert sample.estimated_cost == 0.004


def test_mean() -> None:
    assert mean([1.0, 2.0, 3.0]) == 2.0


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([10.0, 20.0, 30.0, 40.0], 0.95) == 40.0


def test_metrics_snapshot_is_deterministic() -> None:
    collector = MetricsCollector()
    collector.record(
        latency_ms=100,
        success=True,
        cost=CostSample(1000, 500, 0.002, 0.004),
    )
    collector.record(latency_ms=300, success=False)
    snapshot = collector.snapshot()
    assert snapshot.requests == 2
    assert snapshot.successes == 1
    assert snapshot.failures == 1
    assert snapshot.success_rate == 0.5
    assert snapshot.mean_latency_ms == 200
    assert snapshot.p95_latency_ms == 300
    assert snapshot.estimated_cost == 0.004


def test_negative_latency_is_rejected() -> None:
    collector = MetricsCollector()
    try:
        collector.record(latency_ms=-1, success=True)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative latency must be rejected")



def test_prometheus_export_is_stable() -> None:
    collector = MetricsCollector()
    collector.record(latency_ms=100, success=True)
    collector.record(latency_ms=300, success=False)
    output = collector.prometheus()
    assert "attractor_requests_total 2" in output
    assert "attractor_success_rate 0.5" in output
    assert "attractor_p95_latency_ms 300" in output
    assert output.endswith("\n")
