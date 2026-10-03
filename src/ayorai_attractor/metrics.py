"""Small deterministic observability and cost metrics for R8."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CostSample:
    input_tokens: int
    output_tokens: int
    input_price_per_1k: float
    output_price_per_1k: float

    @property
    def estimated_cost(self) -> float:
        return (
            self.input_tokens * self.input_price_per_1k / 1000
            + self.output_tokens * self.output_price_per_1k / 1000
        )


@dataclass(frozen=True)
class MetricsSnapshot:
    requests: int
    successes: int
    failures: int
    mean_latency_ms: float
    p95_latency_ms: float
    estimated_cost: float

    @property
    def success_rate(self) -> float:
        return self.successes / self.requests if self.requests else 0.0


@dataclass
class MetricsCollector:
    """In-process metrics collector with deterministic snapshot semantics."""

    _latencies_ms: list[float] = field(default_factory=list)
    _requests: int = 0
    _successes: int = 0
    _failures: int = 0
    _estimated_cost: float = 0.0

    def record(
        self,
        *,
        latency_ms: float,
        success: bool,
        cost: CostSample | None = None,
    ) -> None:
        if latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        self._requests += 1
        if success:
            self._successes += 1
        else:
            self._failures += 1
        self._latencies_ms.append(latency_ms)
        if cost is not None:
            self._estimated_cost += cost.estimated_cost

    def snapshot(self) -> MetricsSnapshot:
        return MetricsSnapshot(
            requests=self._requests,
            successes=self._successes,
            failures=self._failures,
            mean_latency_ms=mean(self._latencies_ms)
            if self._latencies_ms
            else 0.0,
            p95_latency_ms=percentile(self._latencies_ms, 0.95)
            if self._latencies_ms
            else 0.0,
            estimated_cost=self._estimated_cost,
        )


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("at least one value is required")
    return sum(values) / len(values)


def percentile(values: list[float], quantile: float) -> float:
    """Return the nearest-rank percentile without interpolation."""
    if not values:
        raise ValueError("at least one value is required")
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between 0 and 1")
    ordered = sorted(values)
    rank = max(1, int(len(ordered) * quantile + 0.999999))
    return ordered[rank - 1]
