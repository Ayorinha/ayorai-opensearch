# RN-001 — Second-Layer Questioning for Low-Confidence Verdicts

**Status:** Research proposal · Not a decision · Not scheduled · No implementation authorized  
**Author:** Anderson Leon Ayora · **Date:** 2026-10-11 · **Applies to:** Judge 2.0.0 (ADR-009)

## Summary

AYORAI ATTRACTOR separates intelligence from authorization: probabilistic components may read, extract, and flag, but only the deterministic Judge issues a verdict. This note frames an open research question: how can a system built on that principle question its own low-confidence verdicts without ever weakening its safeguards? It specifies triggers, admissible mechanisms, invariants, traceability, and success criteria so that any future implementation can be evaluated against a fixed standard.

## 1. Problem

The deterministic Judge is reproducible and tamper-evident, but two adversarial failure modes are beyond the reach of counting rules:

- **FM-2 — Out-of-context citation:** an authentic excerpt matches the atomic claim, while its surrounding text qualifies or negates it. Expected outcome: a false `SUPPORTED`.
- **FM-3 — Apparent independence:** sources that appear independent share a single origin, inflating support clusters.

## 2. Research question

Can an opt-in questioning layer reduce FM-2 and FM-3 errors while preserving the invariants below, at an abstention cost that is measured and declared?

## 3. Invariants (non-negotiable)

- **I-1 Authority:** no questioning mechanism creates, changes, or strengthens `SUPPORTED`, `REFUTED`, or `CONFLICTING`.
- **I-2 Asymmetry:** the only permitted effect is to move a result to `ABSTAINED`/`UNVERIFIED`, with a dedicated reason code and a human-review flag (ADR-009, P2).
- **I-3 Traceability:** every activation is recorded and hashed.
- **I-4 Determinism first:** a probabilistic mechanism is admissible only where deterministic mechanisms cannot decide.
- **I-5 Fail-safe:** adversarial triggering can only increase caution, never credulity.

## 4. Triggers

Activation is limited to low-confidence regions:

- `REFUTED` or `CONFLICTING` verdicts;
- `SUPPORTED` with robustness `R1` or `R2`;
- any atom with `claim_type = legal_reference`.

**Rationale:** FM-2 produces a false `SUPPORTED`; a trigger restricted to `REFUTED`/`CONFLICTING` would miss the most harmful error.

## 5. Admissible mechanisms, in order of preference

- **M-a Context-window rule (deterministic):** qualifying language adjacent to the excerpt (for example, “salvo”, “exceto”, “em regra”, “ressalvado”, “desde que”, and “parágrafo único”) triggers abstention. This complements the normative-reference parser (F4.5).
- **M-b Shared-origin detection (deterministic):** near-duplicate text detection (shingling/MinHash) and publication order collapse duplicated sources into a single origin cluster (ADR-006).
- **M-c Human-review queue.**
- **M-d Language model, last resort:** use only for residual cases that M-a through M-c cannot resolve; a local model is preferred for data protection (LGPD).

## 6. Traceability record (per activation)

Record: `trigger` · `mechanism` · `input_sha256` · `output_sha256` · `reason_code` · `effect on the result` · `timestamp`. For M-d, also record the model ID, model revision, and prompt hash (ADR-007 fields). The record is part of the audit trail and is covered by replay integrity.

## 7. Success criteria (to be pre-registered before any measurement)

On the PT-BR benchmark, stratified by `claim_type`, with 95% confidence intervals:

- **Primary:** reduction in the false-`SUPPORTED` rate for FM-2 and FM-3 cases;
- **Constraint:** the increase in abstention rate is reported and bounded by a pre-declared limit;
- **Guardrail:** zero violations of I-1 and I-2, verified by tests.

A mechanism that reduces errors only by abstaining indiscriminately does not meet these criteria.

## 8. Risks

Reduced coverage due to additional abstentions · operational cost · non-determinism of M-d (recorded, not reproducible) · data protection risks when using external models · adversarial over-triggering (bounded by I-5).

## 9. Non-goals

No legal interpretation, normative hierarchy, or revocation analysis (D11). No changes to the Judge rules. No automatic verdict from any model.

## 10. Status and next step

This is an open research question and a candidate topic for the university research agenda. Any implementation requires a new maintainer decision (DEC), an ADR, and pre-registration.
