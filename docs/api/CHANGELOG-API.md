# API changelog

All public API contract changes are additive unless explicitly identified otherwise.

## 2026-10-12 — Item 2.5: r2-a on `POST /v1/verify`

- Added the `r2-a` request contract alongside the existing `r1-a` request contract.
- The request body accepts either `VerificationRequest` (`r1-a`) or `Judge2VerificationRequest` (`r2-a`) through an OpenAPI `oneOf`.
- Existing `r1-a` responses are preserved byte-for-byte against the captured baseline.
- The `r2-a` response exposes the canonical Judge 2 result and a nullable `response_policy`.
- Documented the `r1-a` and `r2-a` response envelope as an additive `oneOf`, plus the applicable 404 and 422 responses for audit/verification endpoints.
- Made nested `r2-a` atom and stance objects reject undeclared properties.

- Bounded all public `r2-a` offsets to the RFC 8785 safe-integer range `0..9007199254740991`.
- Documented the cross-field `end_offset > start_offset` invariant; it remains enforced in application validation because OpenAPI/JSON Schema cannot express the comparison.
- Schemathesis keeps `--checks all`; only `positive_data_acceptance` is excluded for `POST /v1/verify`, while all checks (including positive data acceptance) run for every other operation. The policy is versioned in `scripts/run_schemathesis_contract.sh`.
- Preserved the legacy `require_primary_source` boolean coercion on search requests; the OpenAPI snapshot documents the original boolean field without strict-mode widening or narrowing.
