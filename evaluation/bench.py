from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationDimension:
    name: str
    description: str


DIMENSIONS = [
    EvaluationDimension("accuracy", "Correctness against a trusted reference."),
    EvaluationDimension("evidence", "Quality, provenance and independence of evidence."),
    EvaluationDimension("reasoning", "Consistency and validity of intermediate reasoning."),
    EvaluationDimension("tool_use", "Correct and authorized tool execution."),
    EvaluationDimension("reliability", "Repeatability and failure recovery."),
    EvaluationDimension("robustness", "Resistance to adversarial or malformed inputs."),
    EvaluationDimension("safety", "Policy compliance and safe execution boundaries."),
    EvaluationDimension("recovery", "Ability to retry, fallback and replan."),
    EvaluationDimension("latency", "End-to-end response latency."),
    EvaluationDimension("cost", "Resource and provider cost efficiency."),
    EvaluationDimension("reproducibility", "Ability to reproduce a measured result."),
]


def benchmark_dimensions() -> list[str]:
    return [dimension.name for dimension in DIMENSIONS]
