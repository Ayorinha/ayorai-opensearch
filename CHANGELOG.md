# Changelog

All notable changes to AYORAI ATTRACTOR are documented here.

## [Unreleased]

### Governance

- Added authorship, trademark, DCO, licensing and release-provenance documentation.

## [0.2.0] - 2026-10-03

### Verification

- F0 stabilization release candidate: deterministic claim-as-input verification boundary, provenance-preserving evidence, and auditable Golden evaluation.
- File-wide Ruff suppression removed from the verification and evaluation paths.
- ADR-004 records the claim-as-input contract.

### Verification

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
