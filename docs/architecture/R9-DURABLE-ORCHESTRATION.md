# R9 — Durable orchestration state

The R9 foundation separates orchestration control state from verification data.

## State machine

queued -> running -> succeeded|failed

A job can only be claimed from queued and can only be finished from running. Invalid transitions fail explicitly rather than silently mutating state.

## Idempotency

Each job has an application-provided idempotency key. Re-enqueueing the same key returns the original job instead of creating duplicate work.

## Persistence boundary

The SQLite store contains job identifiers, idempotency keys, status, and attempt count. It deliberately does not store prompts, evidence excerpts, credentials, or model outputs. Those belong to the governed audit/replay boundaries.

## Restart and retry boundary

A durable worker can reconstruct control state after process restart by reading the job record. Retry policy, leases, backoff, and queue delivery remain deployment-level concerns and must transition jobs through this state machine rather than writing ad-hoc status fields.

## Scope

This is the deterministic state primitive for R9. Distributed workers, leases, retry backoff, and queue adapters are subsequent increments; they should consume this state machine rather than invent a second source of truth.
