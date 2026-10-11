# Phase 1 Closure — AYORAI ATTRACTOR

**Status:** PREPARED / NOT CLOSED  
**Reference main SHA at preparation:** 35f03c6b662a7abd0fd8526ee8f020d9ae5619ad  
**Release target:** v0.4.0 (documentation prepared; not released)

This file is a closure checklist and evidence index. It does not turn a pending review into an approval and does not claim that Phase 1 is closed before all gates pass.

## Merged and recorded changes

| Work item | Evidence | State and limit |
|---|---|---|
| F1.4 — deterministic verdict authority guard | PR #144, merge commit 974a3c65d55309a45796b0a59a51177faa3a69da; tests/test_verdict_authority.py | Merged. The guard detects tested AST patterns for unauthorized Verdict construction/member access and prohibited Judge imports. It is not a proof against every possible runtime bypass. |
| F1.4/F4.2 — deterministic input validation and format checks | PR #146, merge commit 35f03c6b662a7abd0fd8526ee8f020d9ae5619ad | Merged. The recorded review reports rejection of malformed date/URI sentinels; this document does not extend that evidence beyond the tested cases. |
| ResponsePolicy and structured invalid-input responses | PR #145, merge commit 76b79d5cb5293c9291e54bcf6813d251563e178a, plus related fixes in current main history | Merged according to repository history. /v1/verify uses structured 422 for the five classified invalid Judge input categories; unexpected ValueError is not generalized into 422. |

## Remaining gates before declaring Phase 1 closed

1. **Q1 — PR #147:** fake-backed tests for verification/security.py, translation.py, and nli.py; per-module floors of 90%, 80%, and 80%; repository coverage ratchet 85%. At preparation time, head SHA is 62cff59a6329adb87253fbd147dd324fd8b40bf3 and GitHub Actions is running. CI must pass on the final head SHA. The independent reviewer must run the full pytest suite, Ruff, mypy, and inspect per-module coverage on that exact SHA.
2. **F1.5 — this documentation change:** version metadata, migration/release notes, traceability updates and this checklist must pass CI and review. A version number in source metadata is not a release or a tag.
3. **DEC-007:** maintainer decision required before creating a GitHub release or tag. The technical recommendation is to publish v0.4.0 only after Q1 and F1.5 have passed and the maintainer explicitly approves it.

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
