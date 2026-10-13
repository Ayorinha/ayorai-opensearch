# Phase 1 Closure — AYORAI ATTRACTOR

**Status:** PREPARED / NOT CLOSED  
**Reference main SHA after Q1 merge:** da05861e249a53d8a2f9ee57eb1a5e2a811e2651  
**Release target:** v0.4.0 (documentation prepared; not released)

**State note (2026-10-13):** v0.4.0 published on 2026-10-11.

This file is a closure checklist and evidence index. It does not turn a pending review into an approval and does not claim that Phase 1 is closed before all gates pass.

## Phase 1 implementation history

| PR | Merge commit / reference | Verified scope |
|---|---|---|
| #123 | `82bff0f`; frozen legacy baseline tag `baseline-legacy-v0` → `3be512b` | Freeze legacy baseline; preserve historical behavior as an immutable reference. |
| #124 | `4d47424` | Pin CI runner to `ubuntu-24.04`. |
| #125 | `2c01b67` | Contract 1.2a: no factual verdict outside the deterministic Judge. |
| #126 | `22be21d` | SQLite audit DB v2: idempotent schema migration, preserved `legacy_verification`, versioned replay and tamper detection through `verify()/replay_integrity`. |
| #127 | `3c9547e` | ADR-009 accepted as the deterministic adjudication contract. |
| #128 | `f4afcad` | PROV-O provenance mapping. |
| #129 | `2ac98ad` | Remove `VerificationStatus` and `EvidenceStore.status()`; eliminate the legacy factual-status path. |
| #132 | `62b0cd3` | Freeze the r1-a snapshot. |
| #136 | `d4964b0` | Introduce `ResponsePolicy` for transport-level abstention, separate from factual verdicts. |
| #139 | `53d0a74` | Structured HTTP 422 for the five classified invalid Judge input categories (DEC-005). |
| #141 | `b0821d1` | Mark Q2 modules outside the verified scope. |
| #144 | `974a3c6` | AST authority guards and CLI contract; tested restrictions are not a proof against every possible runtime bypass. |
| #147 | `da05861e249a53d8a2f9ee57eb1a5e2a811e2651` | Q1 verification-backend tests and per-module coverage gates; independent review approved exact head `69cdee7a3c9549ff7c9a41a6c14b8cca18993a91`; CI passed before SQUASH merge. |

## Related documentation and Phase 4 records

| PR | Merge commit | Scope — not to be mislabeled as Phase 1 implementation |
|---|---|---|
| #130 | `e91e9cb5866808881f55f87925e3c54c7b9de6de` | Pending architecture and governance decisions. |
| #131 | `c3978ed6ffe0307001ccaad46a7c5797e1de4ce1` | Separate manifest for Golden v0.1. |
| #133 | `bfd1a9e6937f82337b628be90ea840ecfeac7e2e` | Neutral authorship and review attribution. |
| #135 | `4f7abfcce63274dc4440dd5900d3d58bcbb211f7` | Record DEC-005 option A. |
| #137 | `894fff5d1c8d7e30d8157b9ebf1653010bcb3894` | Align status pages with the traceability master. |
| #138 | `f40678e582108677162f6db62e97a7c5c722226f` | Audit public claims and evidence sources. |
| #140 | `8b26745f94812aaddcc9a7e275f02d962db0ed92` | Legal-domain scope and citation rules. |
| #145 | `76b79d5cb5293c9291e54bcf6813d251563e178a` | PT-BR annotation protocol draft; not ResponsePolicy. |
| #146 | `35f03c6b662a7abd0fd8526ee8f020d9ae5619ad` | PT-BR source registry and primary-source candidates; not input validation. |

ResponsePolicy belongs to PR #136, and structured HTTP 422 belongs to PR #139. Historical merge references above were checked against GitHub pull-request metadata.

## Remaining gates before declaring Phase 1 closed

1. **Q1 — PR #147:** merged by SQUASH at `da05861e249a53d8a2f9ee57eb1a5e2a811e2651`. Independent review approved exact head `69cdee7a3c9549ff7c9a41a6c14b8cca18993a91`; the approval was recorded by the maintainer. The independent review's local verification recorded 448 passed, 91% total coverage, 100% for `security.py`, `translation.py` and `nli.py`, plus Ruff, mypy and `lint_golden` passing. GitHub Actions was green on that head; frozen artifacts were not changed.
2. **F1.5 — this documentation change:** version metadata, migration/release notes, traceability updates and this checklist must pass CI and review. A version number in source metadata is not a release or a tag.
3. **DEC-007:** explicit maintainer decision is still required before creating a GitHub release or tag. The technical recommendation is to publish v0.4.0 only after F1.5 is reviewed and merged and Phase 1 is formally checked.

## v0.4.0 scope prepared for review

- Removed VerificationStatus and EvidenceStore.status(); use the deterministic /v1/verify contract instead.
- Separated factual Verdict from transport-level ResponsePolicy; retained ResponseStatus as deprecated compatibility surface until v0.5.0.
- Documented the OpenAPI status schema update and structured HTTP 422 for the five classified invalid input categories.
- Documented migration steps and the deprecation/removal horizon for verification, confidence, and ResponseStatus.
- No automatic release, Git tag, Golden regeneration, corpus edits, threshold edits, or frozen-manifest changes are authorized by this document.

## Limitations retained

- Golden v0/v0.1 are development/evaluation-development sets (n=30 claims with global verdict), not a production-generalization benchmark.
- The current corpus consists of synthetic documents tagged en-US; results do not establish generalization to Portuguese source documents.
- Path A remains EVAL_ONLY; Path B is only a candidate commercial path subject to independent license/provenance verification.
- The current Judge does not yet record versioned rule_id traces or the full rule-by-rule explanation required by the future Judge 2.0 work.
- End-to-end independent reconstruction of a verdict is still not established by one dedicated test.

## Phase 2 backlog

The Judge 2.0 backlog remains separate: versioned rule table and interpreter, G/E/A/R/K decision codes, canonical output and digests, rule_trace, response baseline r2-a, explicit migration artifacts, generated truth table, stratified evaluation with n and 95% confidence intervals, schemas, SBOM/dependency inventory, offline networking checks, and reproducibility documentation. None of these are claimed as implemented by v0.4.0.
