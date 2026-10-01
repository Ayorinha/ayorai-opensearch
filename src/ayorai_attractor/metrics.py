"""Small deterministic metrics primitives for R8."""

from dataclasses import dataclass


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


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("at least one value is required")
    return sum(values) / len(values)
