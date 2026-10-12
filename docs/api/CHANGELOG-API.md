# API changelog

All public API contract changes are additive unless explicitly identified otherwise.

## 2026-10-12 — Item 2.5: r2-a on `POST /v1/verify`

- Added the `r2-a` request contract alongside the existing `r1-a` request contract.
- The request body accepts either `VerificationRequest` (`r1-a`) or `Judge2VerificationRequest` (`r2-a`) through an OpenAPI `oneOf`.
- Existing `r1-a` responses are preserved byte-for-byte against the captured baseline.
- The `r2-a` response exposes the canonical Judge 2 result and a nullable `response_policy`.
