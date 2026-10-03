# R11 — Optimization core

ATTRACTOR's R11 foundation makes optimization explicit and reproducible.

A candidate is an immutable identifier plus value. An evaluator supplies a numeric score. The optimizer evaluates every candidate and selects the highest score; ties are resolved by candidate identifier so the result is deterministic.

This module is intentionally evaluator-driven. It does not call an LLM, mutate prompts, inspect hidden state, or change the verification Judge. A future GEPA integration can provide a proposal/evaluation loop while retaining this explicit selection contract.

## Safety boundary

Optimization may improve retrieval, synthesis, routing, or prompt candidates, but it must never bypass evidence validation or replace the deterministic verification Judge.
