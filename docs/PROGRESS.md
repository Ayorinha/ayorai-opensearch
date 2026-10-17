# AYORAI ATTRACTOR — Progress

Updated: 2026-10-17

## Canonical progress record

The [TRACEABILITY MASTER](TRACEABILITY-MASTER.md) is the single source of truth for requirements, implementation mapping, tests, evidence labels, known limitations, and items not implemented or not independently verified.

This page intentionally does not maintain a second feature-by-feature status table or duplicate mutable benchmark, test-count, coverage, or baseline numbers. Those details must be recorded once in the canonical matrix with a precise source, SHA, test, or workflow reference.

## Release and evidence references

- **Published release:** v0.5.0 — [Zenodo DOI 10.5281/zenodo.23344005](https://doi.org/10.5281/zenodo.23344005).
- **DEC-010 approved:** option A, targeting approximately one-third compound claims. [PR #204](https://github.com/Ayorinha/ayorai-opensearch/pull/204) records the decision; [PR #203](https://github.com/Ayorinha/ayorai-opensearch/pull/203) adds executor `rgc-eval/0.2.0` and the `atoms` field; [PR #205](https://github.com/Ayorinha/ayorai-opensearch/pull/205) records Protocol Amendment 3.
- **Exploratory pilot completed:** Anderson annotated 20 cases on 2026-10-16. Distribution: 9 SUPPORTED, 11 REFUTED, 0 UNVERIFIED, 0 PARTIALLY_SUPPORTED, 0 CONFLICTING, 0 RULE_GAP. The pilot contained no cases designed for PARTIALLY_SUPPORTED or CONFLICTING. The results are discarded, labels are not in the repository, and the system was not run on the cases. This is not a system evaluation.
- **Pilot findings / pending DEC-011:** [PR #206](https://github.com/Ayorinha/ayorai-opensearch/pull/206) records three annotation-guide findings: (1) not confirmed is not the same as contradicted (pilot-18); (2) rectification (pilot-19), with option A chosen by Anderson on 2026-10-17 in [PR #207](https://github.com/Ayorinha/ayorai-opensearch/pull/207); and (3) values, quantifiers and modality (pilot-04, pilot-12), with one open point still undecided. DEC-011 remains pending as a whole.
- **RGC preparation:** [PR #176](https://github.com/Ayorinha/ayorai-opensearch/pull/176) records DEC-002; [PR #177](https://github.com/Ayorinha/ayorai-opensearch/pull/177) addresses capture; [PR #178](https://github.com/Ayorinha/ayorai-opensearch/pull/178) documents derived text; [PR #179](https://github.com/Ayorinha/ayorai-opensearch/pull/179) proposes the executor. These references do not mean the protocol is frozen or that benchmark results exist. [PR #192](https://github.com/Ayorinha/ayorai-opensearch/pull/192) addresses canonical URL serialization; [PR #193](https://github.com/Ayorinha/ayorai-opensearch/pull/193) contains Amendment 2; [PR #194](https://github.com/Ayorinha/ayorai-opensearch/pull/194) records DEC-007, DEC-008 and DEC-009; [PR #195](https://github.com/Ayorinha/ayorai-opensearch/pull/195) addresses counts by original Judge state.
- **No Portuguese benchmark result exists.** The exploratory pilot was not run through the system and cannot be used as a performance result.
- **Next steps:** approve DEC-011 in full; prepare Amendment 4; run a second pilot of about 10 cases; freeze the protocol; prepare 300 definitive cases; obtain a second annotator and require Cohen's kappa >= 0.6; then run the system once.

## Execution discipline

- Work follows the approved queue in the current execution plan.
- Changes to frozen artifacts require explicit maintainer authorization and a dedicated review gate.
- A feature is not complete merely because documentation or a test file exists; evidence must identify the actual code path and exact commit tested.
- Independent review, CI results, and maintainer-reported status are distinct evidence categories.

See [Engineering Status](STATUS.md) for the current execution index and [Milestones](MILESTONES.md) for historical milestone references.
