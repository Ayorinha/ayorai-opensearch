# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-03

## Current verification boundary

The claim-level API treats caller-supplied claims as the object of verification:
verify(claims, documents).

ClaimExtractor is response-only and never receives evidence.

ADR-003 defines SUPPORTS, CONTRADICTS and NEUTRAL. Neutral edges are ignored
by the deterministic Judge; zero support and zero contradiction yields
UNVERIFIED.

Numeric contradiction checks now require matching numeric unit and attribute
context. Evidence-vs-evidence baseline comparison is removed from the stance
detector.

## Evaluation truth

Golden v0 is DEV data. The versioned pre-fix reproduction is:
scripts/reproduce_p0c_prefixed_golden.py

Observed pre-fix result:
- new pipeline: 9/30 = 30.0000%;
- legacy: 13/30 = 43.3333%;
- legacy correct/new wrong: 6;
- new correct/legacy wrong: 2;
- exact McNemar p = 0.28906250.

These values are diagnostic only and are not tuning targets.

## Quality gates

Every defect fix requires a regression test and CI evidence before merge.
Infrastructure feature work is frozen until the hidden-test and external
benchmark gates in the ATTRACTOR v1.0 definition are met.
