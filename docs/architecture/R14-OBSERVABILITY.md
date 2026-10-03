# R14 — Provider-neutral tracing context

## Goal

Give every ATTRACTOR execution one correlation ID and a deterministic in-process
event snapshot without coupling the core to an observability vendor.

## Contract

`TraceContext` owns:

- a `trace_id` with the same `tr_...` shape already returned by API responses;
- ordered `TraceEvent` records;
- normalized, sorted string attributes;
- an immutable tuple snapshot for exporters.

The tracing layer does **not** decide verification, mutate evidence, persist
prompts, or call a telemetry backend.

## Integration

The orchestrator creates one trace context per execution and records:

1. `request.started`
2. `provider.ready` or `request.failed`
3. `agents.selected`
4. `verification.completed`

The response `trace_id` is the same correlation identifier.

## Future exporter boundary

An OpenTelemetry exporter can consume `TraceContext.snapshot()` without
changing the deterministic Judge or the API contract. Exporting telemetry is
an operational concern and must remain downstream of verification semantics.
