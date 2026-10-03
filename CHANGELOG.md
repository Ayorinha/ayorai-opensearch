# Changelog

All notable changes to AYORAI ATTRACTOR are documented here.

## [Unreleased]

### Verification

- Versioned pre-fix Golden reproduction records the 9/30 claim-pipeline result.
- Claim verification accepts caller-supplied claims separately from evidence.
- Claim extraction is response-only and cannot read evidence.
- ADR-003 adds NEUTRAL stance semantics.
- Numeric contradiction detection aligns unit and attribute context.
- Negation detection uses token boundaries rather than substring matching.

### Engineering

- Deterministic R1 verification contracts stabilized.
- Numeric/date locale handling hardened.
- Explicit abstention response contracts.
- Full Golden v0 regression remains available as a diagnostic artifact.

## [0.1.0] - 2026-09-30

### Added

- Phase 0 baseline and reproducibility artifacts;
- FastAPI API and CLI;
- provider contracts and deterministic mock provider;
- evidence store and evidence graph;
- deterministic verification foundation;
- security and community health files.

[0.1.0]: https://github.com/Ayorinha/ayorai-opensearch/releases/tag/v0.1.0
