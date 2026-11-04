# AYORAI ATTRACTOR — Progress

Updated: 2026-11-04

> **Current status source:** use [docs/STATUS.md](STATUS.md). This page preserves the historical progress narrative and references; it is not an independent source of current status.

## Canonical progress record

[TRACEABILITY-MASTER.md](TRACEABILITY-MASTER.md) is a historical snapshot of the early traceability review (PR #120), not the current rule-level source. For Judge 2.0.0, use [docs/judge2/TRACEABILITY.md](judge2/TRACEABILITY.md), generated and checked by `scripts/gen_judge2_traceability.py --check`. Use [docs/STATUS.md](STATUS.md) for the current overall project state.

This page intentionally does not maintain a second feature-by-feature status table or duplicate mutable benchmark, test-count, coverage, or baseline numbers. Consult [docs/STATUS.md](STATUS.md) for current status and the generated Judge 2.0.0 traceability for rule-level mappings.

## Release and evidence references

- **Current published release:** v0.6.0 — [version DOI 10.5281/zenodo.23607357](https://doi.org/10.5281/zenodo.23607357). The concept DOI is [10.5281/zenodo.23125082](https://doi.org/10.5281/zenodo.23125082).
- **DEC-010 approved:** option A, targeting approximately one-third compound claims. [PR #204](https://github.com/Ayorinha/ayorai-opensearch/pull/204) records the decision; [PR #203](https://github.com/Ayorinha/ayorai-opensearch/pull/203) adds executor `rgc-eval/0.2.0` and the `atoms` field; [PR #205](https://github.com/Ayorinha/ayorai-opensearch/pull/205) records Protocol Amendment 3.
- **Exploratory pilot completed:** Anderson annotated 20 cases on 2026-10-16. Distribution: 9 SUPPORTED, 11 REFUTED, 0 UNVERIFIED, 0 PARTIALLY_SUPPORTED, 0 CONFLICTING, 0 RULE_GAP. The pilot contained no cases designed for PARTIALLY_SUPPORTED or CONFLICTING. The results are discarded, labels are not in the repository, and the system was not run on the cases. This is not a system evaluation.
- **Pilot findings / DEC-011 approved (2026-10-17):** [PR #206](https://github.com/Ayorinha/ayorai-opensearch/pull/206) records three annotation-guide findings: (1) not confirmed is not the same as contradicted (pilot-18); (2) rectification (pilot-19), option A in [PR #207](https://github.com/Ayorinha/ayorai-opensearch/pull/207); and (3) values, quantifiers and modality (pilot-04, pilot-12), with claims that turn "preferencialmente" into an obligation excluded from v1. Anderson approved all three parts; Protocol Amendment 4 was merged in [PR #227](https://github.com/Ayorinha/ayorai-opensearch/pull/227).
- **RGC preparation:** [PR #176](https://github.com/Ayorinha/ayorai-opensearch/pull/176) records DEC-002; [PR #177](https://github.com/Ayorinha/ayorai-opensearch/pull/177) addresses capture; [PR #178](https://github.com/Ayorinha/ayorai-opensearch/pull/178) documents derived text; [PR #179](https://github.com/Ayorinha/ayorai-opensearch/pull/179) proposes the executor. These references do not mean the protocol is frozen or that benchmark results exist. [PR #192](https://github.com/Ayorinha/ayorai-opensearch/pull/192) addresses canonical URL serialization; [PR #193](https://github.com/Ayorinha/ayorai-opensearch/pull/193) contains Amendment 2; [PR #194](https://github.com/Ayorinha/ayorai-opensearch/pull/194) records DEC-007, DEC-008 and DEC-009; [PR #195](https://github.com/Ayorinha/ayorai-opensearch/pull/195) addresses counts by original Judge state.
- **No Portuguese benchmark result exists.** The exploratory pilot was not run through the system and cannot be used as a performance result.
- **Human-controlled RGC gates (not automation tasks):** Pilot 02, case annotation, second annotator, adjudication, F-01 review, and protocol freeze require explicit human action. They must not be created, simulated, pre-filled, or executed by automation.
- **External exploratory evaluation — AVERITEC-BR (2026-11-04):** skipped pending explicit licensing confirmation for the PT-BR derivative. The STIL 2025 paper and public repositories were located, but the repository containing the translated dataset has no declared license. No dataset was downloaded or executed; no external validation is claimed.

## Execution discipline

- Work follows the approved queue in the current execution plan.
- Changes to frozen artifacts require explicit maintainer authorization and a dedicated review gate.
- A feature is not complete merely because documentation or a test file exists; evidence must identify the actual code path and exact commit tested.
- Independent review, CI results, and maintainer-reported status are distinct evidence categories.

See [Engineering Status](STATUS.md) for the current execution index and [Milestones](MILESTONES.md) for historical milestone references.
