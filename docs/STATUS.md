# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-13

## Source of truth

The [TRACEABILITY MASTER](TRACEABILITY-MASTER.md) is the canonical project requirements and evidence matrix. This page is an index, not an independent source of project metrics, test counts, coverage percentages, benchmark results, or implementation status.

## Current execution

- Latest release: v0.5.0 (2026-10-13), tag on main commit e9eccb5; version DOI 10.5281/zenodo.23344005.
- `main` is protected: pull request required, plus test (3.11), test (3.12), test (3.13), golden-regression, judge-regression and security.
- Next queue: Dependabot updates (#104, #106), then the PT-BR benchmark (Anatel RGC).
- Open work and evidence must be assessed from the exact commit and check run, not inferred from this page.

## Engineering gates

- The deterministic Judge alone owns factual verdicts.
- Frozen evaluation artifacts, manifests, and hashes must not be changed to make tests pass.
- A merge requires independent approval of the exact PR SHA and green required checks.
- A CI result is evidence for the commit tested; it is not automatically an independent review.
- Do not claim performance, legal compliance, production readiness, or institutional partnership without appropriate evidence.

For requirement-level status, implementation paths, tests, evidence, and limitations, use the [TRACEABILITY MASTER](TRACEABILITY-MASTER.md).
