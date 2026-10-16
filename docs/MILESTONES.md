# AYORAI ATTRACTOR — Milestones

Updated: 2026-10-16

## Canonical status

The [TRACEABILITY MASTER](TRACEABILITY-MASTER.md) is the single source of truth for the project's requirements, implementation state, evidence, limitations, and remaining work. This page is only a milestone index and must not repeat mutable test counts, coverage percentages, benchmark scores, or claims of completion.

## Release and RGC evidence

- **v0.5.0 published:** [Zenodo DOI 10.5281/zenodo.23344005](https://doi.org/10.5281/zenodo.23344005).
- **RGC preparation references:** [#176 — DEC-002](https://github.com/Ayorinha/ayorai-opensearch/pull/176), [#177 — capture](https://github.com/Ayorinha/ayorai-opensearch/pull/177), [#178 — derived text](https://github.com/Ayorinha/ayorai-opensearch/pull/178), and [#179 — proposed executor](https://github.com/Ayorinha/ayorai-opensearch/pull/179).
- **Subsequent references:** [#192 — canonical URL correction](https://github.com/Ayorinha/ayorai-opensearch/pull/192), [#193 — Amendment 2](https://github.com/Ayorinha/ayorai-opensearch/pull/193), [#194 — DEC-007/008/009](https://github.com/Ayorinha/ayorai-opensearch/pull/194), and [#195 — counts by state](https://github.com/Ayorinha/ayorai-opensearch/pull/195).
- **Open protocol question:** DEC-010 (compound claims) remains pending. It blocks freezing the protocol and drafting the 300 definitive cases, but does not block the exploratory 20-case pilot; pilot results are discarded.
- **Next milestone:** complete and document the exploratory human-annotation pilot on 20 RGC PT-BR cases. No Portuguese benchmark result exists, and the pilot has not yet been conducted.

## Historical evidence

Historical workflow runs and baseline results remain historical evidence for the exact commits and artifacts they tested. They must not be interpreted as proof of the current main branch or a later commit.

- The legacy baseline is preserved by the repository's `baseline-legacy-v0` tag.
- Frozen Golden artifacts and their SHA-256 references are documented in the repository's evaluation manifests and traceability matrix. Golden v0 and v0.1 remain distinct frozen references and must be cited side by side when discussed.
- Current merge and release gates must be checked against the exact PR head SHA and its workflow runs.

## Completion rule

A milestone is complete only when its acceptance criteria, implementation, tests, and required evidence are recorded in the canonical traceability matrix. Publishing a release or tag remains a maintainer action.
