# API changelog

All public API contract changes are additive unless explicitly identified otherwise.

## 2026-10-12 — Item 2.5: r2-a on `POST /v1/verify`

- Added the `r2-a` request contract alongside the existing `r1-a` request contract.
- The request body accepts either `VerificationRequest` (`r1-a`) or `Judge2VerificationRequest` (`r2-a`) through an OpenAPI `oneOf`.
- Existing `r1-a` responses are preserved byte-for-byte against the captured baseline.
- The `r2-a` response exposes the canonical Judge 2 result and a nullable `response_policy`.

## 2026-10-12 — Item 2.7: canonical-result explanations and traceability

- Added a simple explanation of at most five lines and a technical explanation copied only from the canonical Judge 2 result.
- Explanations verify output_sha256 and reject invalid or contradictory canonical objects; ABSTAINED and INVALID_INPUT remain without factual verdicts.
- Added generated rule-to-test-to-Golden traceability for G1–G2, E1–E3, A1–A4, R0–R3 and K1–K5. The generator fails when a normative rule lacks a real test, and CI tests generated-document parity.
- Phase 2 completion is described only after this PR is merged.
