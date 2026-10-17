# AYORAI ATTRACTOR — Engineering Status

Updated: 2026-10-17

## Source of truth

The [TRACEABILITY MASTER](TRACEABILITY-MASTER.md) is the canonical project requirements and evidence matrix. This page is an index, not an independent source of project metrics, test counts, coverage percentages, benchmark results, or implementation status.

## Current execution

- Latest release: v0.5.0 (2026-10-13), tag on main commit e9eccb5; version DOI 10.5281/zenodo.23344005.
- `main` is protected: pull request required, plus test (3.11), test (3.12), test (3.13), golden-regression, judge-regression and security.
- **DEC-010 is approved, option A (~one-third compound claims):** decision [PR #204](https://github.com/Ayorinha/ayorai-opensearch/pull/204); executor `rgc-eval/0.2.0`, including the `atoms` field, [PR #203](https://github.com/Ayorinha/ayorai-opensearch/pull/203); Protocol Amendment 3 [PR #205](https://github.com/Ayorinha/ayorai-opensearch/pull/205).
- **Exploratory 20-case pilot completed on 2026-10-16**, annotated by Anderson. Distribution: 9 SUPPORTED, 11 REFUTED, 0 UNVERIFIED, 0 PARTIALLY_SUPPORTED, 0 CONFLICTING and 0 RULE_GAP. The pilot did not include cases designed to exercise PARTIALLY_SUPPORTED or CONFLICTING. Pilot results are discarded; pilot labels are not in the repository. The system was not run on these cases, so this pilot does not measure system performance.
- Pilot findings are recorded in pending DEC-011 [PR #206](https://github.com/Ayorinha/ayorai-opensearch/pull/206). The maintainer chose option A for Part 2 (rectification) on 2026-10-17 [PR #207](https://github.com/Ayorinha/ayorai-opensearch/pull/207). DEC-011 remains pending: Part 1, Part 3 and one open point in Part 3 still require a decision.
- **No Portuguese benchmark result exists.** The exploratory pilot is discarded and is not a system evaluation. Next steps: approve DEC-011 in full; prepare Amendment 4; run a second pilot of about 10 cases; freeze the protocol; prepare 300 definitive cases; obtain a second annotator and require Cohen's kappa >= 0.6; then run the system once.
- Earlier RGC preparation: [#176](https://github.com/Ayorinha/ayorai-opensearch/pull/176) records DEC-002; [#177](https://github.com/Ayorinha/ayorai-opensearch/pull/177) addresses official source capture and SHA-256; [#178](https://github.com/Ayorinha/ayorai-opensearch/pull/178) documents derived text; [#179](https://github.com/Ayorinha/ayorai-opensearch/pull/179) proposes the executor; [#192](https://github.com/Ayorinha/ayorai-opensearch/pull/192) addresses canonical URL serialization; [#193](https://github.com/Ayorinha/ayorai-opensearch/pull/193) contains Amendment 2; [#194](https://github.com/Ayorinha/ayorai-opensearch/pull/194) records DEC-007, DEC-008 and DEC-009; [#195](https://github.com/Ayorinha/ayorai-opensearch/pull/195) addresses prediction counts by original Judge state.
- Open work and evidence must be assessed from the exact commit and check run, not inferred from this page.

## Engineering gates

- The deterministic Judge alone owns factual verdicts.
- Frozen evaluation artifacts, manifests, and hashes must not be changed to make tests pass.
- A merge requires independent approval of the exact PR SHA and green required checks.
- A CI result is evidence for the commit tested; it is not automatically an independent review.
- Do not claim performance, legal compliance, production readiness, or institutional partnership without appropriate evidence.

For requirement-level status, implementation paths, tests, evidence, and limitations, use the [TRACEABILITY MASTER](TRACEABILITY-MASTER.md).
