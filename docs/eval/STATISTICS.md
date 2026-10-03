# Evaluation Statistics

ATTRACTOR keeps decision logic separate from statistical reporting.

- **6×6 confusion matrix:** fixed to the six ADR-002 Judge verdict states.
- **Bootstrap:** deterministic percentile 95% confidence interval for accuracy; the default is 10,000 resamples with an explicit seed.
- **McNemar:** exact two-sided test for paired predictions from two systems on the same cases.

These functions consume only expected and predicted labels. They do not alter verdicts, call an LLM, or select a benchmark winner.

A benchmark report should publish the dataset/suite version, case count, system commit, point accuracy, bootstrap interval, confusion matrix, and—when comparing two systems on identical cases—the paired McNemar result.
