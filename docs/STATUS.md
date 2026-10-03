# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-03

## Verification boundary

verify(claims, documents) verifies caller-supplied claims. ClaimExtractor is
response-only and never receives evidence.

ADR-003 defines SUPPORTS, CONTRADICTS and NEUTRAL. Neutral edges are ignored by
the deterministic Judge.

Numeric contradiction checks require matching numeric unit and attribute
context. Evidence-vs-evidence baseline comparison is removed.

Negation detection is token-based and cannot treat substrings as negation.

Production parsing/mapping failures abstain with a recorded reason. LLM claim
and stance payloads use strict Pydantic schemas.

## P0.c Golden runner

The official runner now feeds only expected_claims[].text into the verifier.
The per-claim verdict field is never passed to the pipeline. Verdicts are
produced only by the deterministic Judge.

The runner reports:
- accuracy;
- balanced accuracy;
- fixed 6x6 confusion matrix;
- deterministic 10,000-sample bootstrap 95% CI;
- exact paired McNemar versus the legacy runner;
- evaluated abstention contracts.

Golden v0 is DEV data and must not be tuned to improve these numbers.

## Pre-fix reproduction

scripts/reproduce_p0c_prefixed_golden.py records:
- new pipeline: 9/30 = 30.0000%;
- legacy: 13/30 = 43.3333%;
- legacy correct/new wrong: 6;
- new correct/legacy wrong: 2;
- exact McNemar p = 0.28906250.

Those are diagnostic pre-fix numbers, not current post-fix benchmark results.

## CI evidence

P0.c is wired; the post-fix numerical result remains pending the current CI run.

## Quality gates

Every defect fix requires a regression test and CI evidence before merge.
Infrastructure feature work is frozen until hidden-test and external benchmark
gates are met.


## F0 recovery after external review

- Recovery branch: fix/f0-recovery
- Verified HEAD: 7478f7a320285e033a683620b60ad0a60153efe8
- Golden v0: 8/30 (26.6667%), balanced accuracy 44.0171%, bootstrap 95% CI [13.3333%, 43.3333%]
- Abstention contracts: 4/4
- CI run: https://github.com/Ayorinha/ayorai-opensearch/actions/runs/37133387080
- Core test/type/security/CodeQL gates: green
- Dependency Review: blocked because GitHub Dependency Graph is disabled; do not claim F0 fully closed until that repository setting is enabled.
