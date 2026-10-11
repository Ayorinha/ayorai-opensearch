# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-11

## Source of truth

The [TRACEABILITY MASTER](TRACEABILITY-MASTER.md) is the canonical project requirements and evidence matrix. This page is an index, not an independent source of project metrics, test counts, coverage percentages, benchmark results, or implementation status.

## Current execution

- Main branch at the start of this documentation change: `5ab8f32b9cd14a16fe55a108cab6d685cfe3d3bd`.
- Baseline-only r1-a response snapshot: [PR #132](https://github.com/Ayorinha/ayorai-opensearch/pull/132), merged; its fixture must remain unchanged during the separate ResponsePolicy PR.
- DEC-005 option A: documented for maintainer approval and sequencing in a separate documentation PR; the fix itself belongs in its own PR after ResponsePolicy.
- Open work and evidence must be assessed from the exact commit and check run, not inferred from this page.

## Engineering gates

- The deterministic Judge alone owns factual verdicts.
- Frozen evaluation artifacts, manifests, and hashes must not be changed to make tests pass.
- A merge requires independent approval of the exact PR SHA and green required checks.
- A CI result is evidence for the commit tested; it is not automatically an independent review.
- Do not claim performance, legal compliance, production readiness, or institutional partnership without appropriate evidence.

For requirement-level status, implementation paths, tests, evidence, and limitations, use the [TRACEABILITY MASTER](TRACEABILITY-MASTER.md).
