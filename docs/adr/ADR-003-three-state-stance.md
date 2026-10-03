# ADR-003 — Three-state stance semantics

Status: Accepted
Date: 2026-10-03

## Decision

Stance has three states: SUPPORTS, CONTRADICTS and NEUTRAL.

NEUTRAL means that retrieved evidence does not contain enough relevant
information to support or contradict the claim. It is not a final Verdict.

The deterministic Judge ignores NEUTRAL when counting clusters:
support=0 and contradiction=0 produces UNVERIFIED.

The RuleStanceDetector must return NEUTRAL for irrelevant evidence. Learned
detectors may return NEUTRAL when confidence is insufficient.

## Consequence

Golden v0 is development data after the pre-fix circularity result. The rule
detector must not be tuned to individual Golden cases.
