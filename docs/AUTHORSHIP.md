# Authorship & Technical Direction

## Authorship

AYORAI ATTRACTOR was authored and technically directed by **Anderson Leon Ayora**.

The repository's architecture, verification contracts, evaluation criteria and release requirements are maintained under the author's direction. AI tools may be used as implementation assistants, reviewers or research assistants, but they do not replace human authorship, responsibility, review or project governance.

## Decision record

| Date | Decision | Evidence |
|---|---|---|
| 2026-09-30 | **ADR-001 — isolated Python namespace**: use `src/` and the `ayorai_attractor` application namespace to avoid SDK namespace collisions. | [ADR-001](../docs/adr/ADR-001-namespace.md) |
| 2026-09-30 | **ADR-002 — deterministic Judge**: final verdicts are derived from deterministic S/C/P rules; LLM output cannot directly choose the verdict. | [ADR-002](../docs/adr/ADR-002-judge-rules.md), [PR #12](https://github.com/Ayorinha/ayorai-opensearch/pull/12), merge `b7df480` |
| 2026-10-03 | **ADR-003 contract — claim-as-input verification boundary**: `verify(claims, documents)` receives caller-supplied claims; evidence is never used to derive claims inside verification. | [Golden connection commit `9e119a5`](https://github.com/Ayorinha/ayorai-opensearch/commit/9e119a562f0779bd06300944d2997d6d7946c47c), [retriever-guard commit `7374f28`](https://github.com/Ayorinha/ayorai-opensearch/commit/7374f28d702caf397c0d8779137934ee0861d1b8) |
| 2026-10-03 | **100% definition**: project completion is evidence-gated, not an estimate; each required criterion must have executable tests, reproducible commands and CI/release artifacts where applicable. | [STATUS](../docs/STATUS.md), [F0 recovery evidence](../docs/eval/P0C-RESULTS.md) |

### ADR-003 note

The claim-as-input decision is already executable and guarded in CI, but the repository did not contain a file named ADR-003 at the time this authorship record was prepared. The evidence above intentionally links the existing decision/implementation commits rather than inventing a historical ADR file.

## Human review and AI assistance

AI tools have been used as assistants under Anderson Leon Ayora's direction and human review. Architectural decisions, acceptance criteria, repository changes and release decisions remain subject to human review and ownership.

## Citation

For research or software reuse, cite the repository using [CITATION.cff](../CITATION.cff). A Zenodo DOI will be added after the repository is connected and a release is archived.
