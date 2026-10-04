# Changelog

All notable changes to AYORAI ATTRACTOR are documented here.

## [Unreleased]

### Governance

- Added authorship, trademark, DCO, licensing and release-provenance documentation.

### Security

- Added `docs/THREAT-MODEL.md` with scope, assets, threats, current defenses and known gaps.
- `ReplayStore.get` now accepts only 64-character lowercase hex digests (blocking path traversal) and rejects replay files whose internal digest differs from the requested digest.
- All GitHub Actions are pinned to full commit SHAs with version comments.
- Frozen evaluation sets and F1 thresholds are now enforced by SHA-256 tests.
- Added a guard against committing hidden Golden v1 files.
- Added a training-data license manifest gate (`scripts/check_training_manifest.py`).
- Evidence excerpts are now located in the original source; evidence not found verbatim is dropped and recorded in the audit trail (GAP B).

## [0.3.0] - 2026-10-04

### Verification

- NLI is loaded lazily under ADR-005, keeping the optional model stack out of the base import path.
- FACT was rewritten with adversarial tests covering numeric, entity, date, negation, comparison and provenance-sensitive cases.
- Provenance handling was corrected across evidence and stance paths.
- Golden v0.1 was frozen with a pre-registration and explicit development-set disclosure.
- E1 was measured on Golden v0.1 against the 43.33% majority baseline.
- E2 and E3 negative findings are documented; E3 remains a manual/audit-only negative evaluation rather than a promotion result.
- ADR-006, ADR-007 and ADR-008 record the subsequent evaluation, Portuguese span-detection and commercial NLI design decisions.
- E3 manual reconciliation and disclosure were recorded without changing the historical measurement.
- `actionlint 1.7.12` is pinned by direct archive SHA-256 verification.
- `judge-smoke.jsonl` is the public deterministic Judge smoke fixture; the name Golden v1 remains reserved for the future hidden Portuguese evaluation set.

### E1 measurement

Golden v0.1 baseline: **43.33%**.

| Path | Accuracy | Role |
|---|---:|---|
| A | **76.67%** | EVAL_ONLY |
| B | **66.67%** | candidate commercial path |
| C | **33.33%** | deterministic ablation |

Exact one-sided binomial tests versus the 43.33% baseline: **A p=0.0002**; **B p=0.0085**.

### Mandatory limitations

- **A is EVAL_ONLY. B is the candidate commercial path.**
- **Golden v0 and v0.1 are development/evaluation-development sets**, not evidence of production generalization.
- The current corpus contains **English documents with Portuguese claims**. It is therefore not a Portuguese-document generalization benchmark.
- Generalization is reserved for the **hidden Golden v1**, which must contain genuinely Portuguese documents and remain untouched during development.

## [0.2.0] - 2026-10-03

### Verification

- F0 stabilization release candidate: deterministic claim-as-input verification boundary, provenance-preserving evidence, and auditable Golden evaluation.
- File-wide Ruff suppression removed from the verification and evaluation paths.
- ADR-004 records the claim-as-input contract.
- F0 stabilization: fixed numeric cross-evidence comparison, duplicate verification exports, and stale Golden abstention assertions; CI evidence pending on the updated P0 branch.
- Versioned pre-fix Golden reproduction records the 9/30 claim-pipeline result.
- Claim verification accepts caller-supplied claims separately from evidence.
- Claim extraction is response-only and cannot read evidence.
- ADR-003 adds NEUTRAL stance semantics.
- Numeric contradiction detection aligns unit and attribute context.
- Negation detection uses token boundaries.
- Production parsing/mapping failures abstain with a recorded reason.
- LLM claim and stance payloads use strict Pydantic schemas.
- P0.c Golden runner now verifies expected_claims text without consuming verdict labels and reports statistical comparison against the legacy runner.

### Engineering

- Deterministic R1 verification contracts stabilized.
- Numeric/date locale handling hardened.
- Explicit abstention response contracts.
- Full Golden v0 regression remains a diagnostic/development artifact.

## [0.1.0] - 2026-09-30

### Added

- Phase 0 baseline and reproducibility artifacts;
- FastAPI API and CLI;
- provider contracts and deterministic mock provider;
- evidence store and evidence graph;
- deterministic verification foundation;
- security and community health files.

[0.2.0]: https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.2.0
[0.1.0]: https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.1.0
