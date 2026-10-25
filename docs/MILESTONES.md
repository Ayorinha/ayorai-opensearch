# AYORAI ATTRACTOR — Milestones

Updated: 2026-10-17

> **Current status source:** use [docs/STATUS.md](STATUS.md). This page preserves historical milestone context and references; it is not an independent source of current status.

## Canonical status

The [TRACEABILITY MASTER](TRACEABILITY-MASTER.md) is the single source of truth for the project's requirements, implementation state, evidence, limitations, and remaining work. This page is only a milestone index and must not repeat mutable test counts, coverage percentages, benchmark scores, or claims of completion.

## Release and RGC evidence

- **v0.6.0 published:** [Zenodo DOI 10.5281/zenodo.23607357](https://doi.org/10.5281/zenodo.23607357).
- **v0.5.0 published:** [Zenodo DOI 10.5281/zenodo.23344005](https://doi.org/10.5281/zenodo.23344005).
- **DEC-010 approved:** option A, with a target of approximately one-third compound claims. [#204 — decision](https://github.com/Ayorinha/ayorai-opensearch/pull/204), [#203 — executor `rgc-eval/0.2.0` and `atoms`](https://github.com/Ayorinha/ayorai-opensearch/pull/203), and [#205 — Protocol Amendment 3](https://github.com/Ayorinha/ayorai-opensearch/pull/205).
- **Exploratory pilot completed on 2026-10-16:** Anderson annotated 20 cases. Distribution: 9 SUPPORTED, 11 REFUTED, 0 UNVERIFIED, 0 PARTIALLY_SUPPORTED, 0 CONFLICTING, 0 RULE_GAP. No pilot cases were designed for PARTIALLY_SUPPORTED or CONFLICTING. The pilot results are discarded and labels are not in the repository; the system was not executed on the cases. This pilot does not measure system performance.
- **DEC-011 approved on 2026-10-17:** [#206 — annotation-guide findings](https://github.com/Ayorinha/ayorai-opensearch/pull/206) records (1) “not confirmed” versus “contradicted” (pilot-18), (2) rectification (pilot-19; option A, [#207](https://github.com/Ayorinha/ayorai-opensearch/pull/207)), and (3) values/quantifiers/modality (pilot-04, pilot-12; claims that turn “preferencialmente” into an obligation are excluded from v1). Protocol Amendment 4: [#227](https://github.com/Ayorinha/ayorai-opensearch/pull/227).
- **RGC preparation references:** [#176 — DEC-002](https://github.com/Ayorinha/ayorai-opensearch/pull/176), [#177 — capture](https://github.com/Ayorinha/ayorai-opensearch/pull/177), [#178 — derived text](https://github.com/Ayorinha/ayorai-opensearch/pull/178), [#179 — proposed executor](https://github.com/Ayorinha/ayorai-opensearch/pull/179), [#192 — canonical URL correction](https://github.com/Ayorinha/ayorai-opensearch/pull/192), [#193 — Amendment 2](https://github.com/Ayorinha/ayorai-opensearch/pull/193), [#194 — DEC-007/008/009](https://github.com/Ayorinha/ayorai-opensearch/pull/194), and [#195 — counts by original Judge state](https://github.com/Ayorinha/ayorai-opensearch/pull/195).

## Next milestones

1. ~~Approve DEC-011 in full~~ — done 2026-10-17.
2. ~~Prepare Protocol Amendment 4~~ — merged in #227.
3. Run a second human pilot of approximately 10 new cases, including partial, conflicting and rectified cases where legitimate evidence exists; cases are discarded after review.
4. Record the explicit maintainer decision to freeze the protocol.
5. Prepare the 300 definitive cases.
6. Obtain a second annotator; require Cohen's kappa >= 0.6.
7. Execute the system once on the frozen, fully annotated set.

**No Portuguese benchmark result exists.** The exploratory pilot was discarded and the system was not run on its cases.

## Historical evidence

Historical workflow runs and baseline results remain historical evidence for the exact commits and artifacts they tested. They must not be interpreted as proof of the current main branch or a later commit.

- The legacy baseline is preserved by the repository's `baseline-legacy-v0` tag.
- Frozen Golden artifacts and their SHA-256 references are documented in the repository's evaluation manifests and traceability matrix. Golden v0 and v0.1 remain distinct frozen references and must be cited side by side when discussed.
- Current merge and release gates must be checked against the exact PR head SHA and its workflow runs.

## Completion rule

A milestone is complete only when its acceptance criteria, implementation, tests, and required evidence are recorded in the canonical traceability matrix. Publishing a release or tag remains a maintainer action.
