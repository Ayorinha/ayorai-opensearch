# ADR-004 — Claim as Verification Input

- **Status:** Accepted
- **Date:** 2026-10-03
- **Decision:** Verification receives caller-supplied claims and closed-world documents through `verify(claims, documents)).

## Context

ATTRACTOR must audit what an agent asserts without allowing retrieved evidence to manufacture the claims being evaluated. A verifier that derives claims from its own evidence can create circular evidence and hide the boundary between assertion and proof.

## Decision

The verification contract is:

`ClaimVerificationPipeline.verify(claims, documents)`

where:

- `claims` is the authoritative caller-supplied assertion set;
- `documents` is the closed-world evidence set available for verification;
- claim extraction, when used by `verify_response`, receives only the model response and never evidence;
- the deterministic ADR-002 Judge remains the sole component that selects the final verdict.

The same contract applies to PT and EN inputs. Evidence may support, contradict, or fail to verify a supplied claim, but it cannot redefine the claim.

## Consequences

- Claim provenance identifies the caller/input boundary.
- Retriever-derived claims are structurally disallowed from `verify`.
- Golden evaluation can distinguish claim verification from response decomposition.
- Future NLI and hybrid stance components must produce evidence/stance data only; they do not choose the final verdict.

## Supersession

ADR-005 will define the F1 hybrid stance policy: deterministic number, date, unit, and negation rules take priority when triggered; NLI handles the remaining cases.
