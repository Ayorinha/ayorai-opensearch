# R8 — Deterministic observability metrics

R8 starts with a dependency-free metrics core that can be embedded in the ATTRACTOR orchestration path without changing verification semantics.

## Metrics

`MetricsCollector` records request count, successful and failed requests, latency samples in milliseconds, and estimated model cost from token counts and configured prices.

`MetricsSnapshot` exposes success rate, mean latency, nearest-rank p95 latency, and accumulated estimated cost.

## Determinism

The collector receives measurements explicitly; it does not read the clock, environment, network, or model output. Percentiles use nearest-rank semantics with sorted samples. This makes unit tests and replay-oriented diagnostics stable.

This layer is observational only. It must never decide a verification verdict. The deterministic Judge remains the authority for claim verification.

## Next R8 integration

The next increment can attach these primitives to request/agent spans and export them through OpenTelemetry, while preserving the same no-secret and no-raw-prompt persistence boundary used by the audit store.
