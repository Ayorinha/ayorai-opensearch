# R15 — Durable worker executor

`JobStore` already provided durable state, idempotency and restart-safe leases.
R15 connects that state machine to an explicit worker boundary.

## Contract

- `JobExecutor.run()` claims exactly one queued job;
- the claim receives a lease and increments the attempt count;
- the handler owns execution of the governed payload/reference;
- success transitions to `SUCCEEDED`;
- handler failure transitions to `FAILED` and clears the lease;
- expired jobs can be reclaimed through the store;
- the executor does not persist prompts, secrets or model outputs.

This is a local worker boundary, not a claim of distributed scheduling. A
future queue adapter can implement the same contract around the durable store.
