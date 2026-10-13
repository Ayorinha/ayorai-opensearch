# Authorship & Technical Direction

## Authorship

AYORAI ATTRACTOR was authored and technically directed by **Anderson Leon Ayora**.

The repository's architecture, verification contracts, evaluation criteria and release requirements are maintained under the author's direction. AI tools may be used as implementation assistants, reviewers or research assistants, but they do not replace human authorship, responsibility, review or project governance.

## Decision record

| Date | Decision | Evidence |
|---|---|---|
| 2026-09-30 | **ADR-001 — isolated Python namespace**: use `src/` and the `ayorai_attractor` application namespace to avoid SDK namespace collisions. | [ADR-001](adr/ADR-001-namespace.md) |
| 2026-09-30 | **ADR-002 — deterministic Judge**: final verdicts are derived from deterministic S/C/P rules; LLM output cannot directly choose the verdict. | [ADR-002](adr/ADR-002-judge-rules.md), [PR #12](https://github.com/Ayorinha/ayorai-opensearch/pull/12), merge `b7df480` |
| 2026-10-03 | **ADR-003 — three-state stance**: stance semantics include SUPPORTS, CONTRADICTS and NEUTRAL. | [ADR-003](adr/ADR-003-three-state-stance.md) |
| 2026-10-03 | **ADR-004 — claim-as-input verification boundary**: `verify(claims, documents)` receives caller-supplied claims; evidence is never used to derive claims inside verification. | [ADR-004](adr/ADR-004-claim-as-input.md), [PR #88](https://github.com/Ayorinha/ayorai-opensearch/pull/88) |
| 2026-10-03 | **100% definition**: project completion is evidence-gated, not an estimate; each required criterion must have executable tests, reproducible commands and CI/release artifacts where applicable. | [STATUS](STATUS.md), [F0 recovery evidence](eval/P0C-RESULTS.md) |

## Human review and AI assistance

AI tools have been used as assistants under Anderson Leon Ayora's direction and human review. Architectural decisions, acceptance criteria, repository changes and release decisions remain subject to human review and ownership.

Seven commits dated 2026-10-09 carry a technical attribution to an AI tool in the Git history. They are intentionally preserved, not rewritten, because they are part of published releases archived with DOIs; rewriting history would break the project's verifiable integrity.

## Prior intellectual property

The verifiable record of authorship and prior intellectual property (first commit, release tags, Zenodo DOIs and guidance for future institutional agreements) is kept in [docs/legal/PRIOR-IP-RECORD.md](legal/PRIOR-IP-RECORD.md).

## Citation

For research or software reuse, cite the repository using [CITATION.cff](../CITATION.cff). Cite all versions with DOI 10.5281/zenodo.23125082; cite a specific release with its version DOI (v0.5.0: 10.5281/zenodo.23344005; v0.4.0: 10.5281/zenodo.23300849).
