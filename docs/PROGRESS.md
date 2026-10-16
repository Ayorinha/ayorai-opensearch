# AYORAI ATTRACTOR — Progress

Updated: 2026-10-16

## Canonical progress record

The [TRACEABILITY MASTER](TRACEABILITY-MASTER.md) is the single source of truth for requirements, implementation mapping, tests, evidence labels, known limitations, and items not implemented or not independently verified.

This page intentionally does not maintain a second feature-by-feature status table or duplicate mutable benchmark, test-count, coverage, or baseline numbers. Those details must be recorded once in the canonical matrix with a precise source, SHA, test, or workflow reference.

## Release and evidence references

- **Published release:** v0.5.0 — [Zenodo DOI 10.5281/zenodo.23344005](https://doi.org/10.5281/zenodo.23344005).
- **RGC preparation:** [PR #176](https://github.com/Ayorinha/ayorai-opensearch/pull/176) records DEC-002; [PR #177](https://github.com/Ayorinha/ayorai-opensearch/pull/177) addresses capture; [PR #178](https://github.com/Ayorinha/ayorai-opensearch/pull/178) documents derived text; [PR #179](https://github.com/Ayorinha/ayorai-opensearch/pull/179) proposes the executor. These references do not mean the protocol is frozen or that benchmark results exist.
- **Follow-up evidence:** [PR #192](https://github.com/Ayorinha/ayorai-opensearch/pull/192) addresses the canonical URL issue; [PR #193](https://github.com/Ayorinha/ayorai-opensearch/pull/193) contains Amendment 2; [PR #194](https://github.com/Ayorinha/ayorai-opensearch/pull/194) records decisions DEC-007, DEC-008 and DEC-009; [PR #195](https://github.com/Ayorinha/ayorai-opensearch/pull/195) addresses counts by state. Review the linked PRs and their exact workflow runs before treating any change as merged or CI-verified.
- **Pending decision:** DEC-010 on compound claims is pending maintainer decision. It blocks protocol freeze and drafting the 300 definitive cases; it does not block the exploratory 20-case pilot, whose results are discarded.
- **Next step:** run the exploratory human-annotation pilot on 20 RGC PT-BR cases, record the annotation issues, and preserve the fact that no Portuguese benchmark result exists until a properly specified and reviewed evaluation has been run.

## Execution discipline

- Work follows the approved queue in the current execution plan.
- Changes to frozen artifacts require explicit maintainer authorization and a dedicated review gate.
- A feature is not complete merely because documentation or a test file exists; evidence must identify the actual code path and exact commit tested.
- Independent review, CI results, and maintainer-reported status are distinct evidence categories.

See [Engineering Status](STATUS.md) for the current execution index and [Milestones](MILESTONES.md) for historical milestone references.
