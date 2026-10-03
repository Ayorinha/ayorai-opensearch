# R7 — Deterministic red-team corpus

R7 adds a small, deterministic adversarial corpus for the ATTRACTOR security
boundary. The corpus is intentionally executable as a unit-test contract:
attack-shaped text remains data and never becomes an instruction to the
verification runtime.

## Threat classes

- Prompt injection: instruction-shaped evidence is treated as evidence data.
- Evidence poisoning: hostile claims inside a source do not override the Judge.
- Citation manipulation: unknown citation identifiers are rejected.
- Secret exposure: secret-shaped payloads are never persisted by the red-team
  contract.

## Safety invariant

The red-team evaluator checks explicit safe-handling actions only. It does not
execute payloads, call tools, follow instructions from evidence, or make a
verification decision. R7 therefore exercises the boundary without introducing
an attacker-controlled execution path.

## Scope

This corpus is a deterministic security regression layer. It complements, but
does not replace, dependency scanning, Bandit, CodeQL, runtime isolation, or
future property-based/adversarial testing.
