# API changelog

All public API contract changes are additive unless explicitly identified otherwise.

## 2026-10-15 — Fix #182: `evidence[].canonical_url` on `r2-a`

- Fixed: an `r2-a` request with a valid `evidence[].canonical_url` returned `INVALID_INPUT / SCHEMA_VIOLATION` instead of being adjudicated. Cause: the validated `HttpUrl` reached the canonical-input serializer, which rejected the type.
- `canonical_url` now enters the canonical input (and `input_sha256`) as pydantic's normalized URL string, the same form the independence rule compares. Example: `https://example.test` and `https://example.test/` hash identically.
- No request or response schema change; the OpenAPI snapshot is unchanged. No frozen Golden, rules file or rules hash changes. Requests without `canonical_url` keep byte-identical hashes. Only rejection hashes of requests that previously failed with this field change, because those requests are now decided.

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
- Preserved legacy `require_primary_source` coercion: JSON booleans and integer `0`/`1` remain accepted, and the OpenAPI snapshot documents both forms.

## 2026-10-12 — Item 2.7: canonical-result explanations and traceability

- Added a simple explanation of at most five lines and a technical explanation copied only from the canonical Judge 2 result.
- Explanations verify `output_sha256` and reject invalid or contradictory canonical objects; `ABSTAINED` and `INVALID_INPUT` remain without factual verdicts.
- Added generated rule-to-test-to-Golden traceability for G1–G2, E1–E3, A1–A4, R0–R3 and K1–K5. The generator fails when a normative rule lacks a real test, and CI tests generated-document parity.
- Phase 2 completion is described only after this PR is merged.

## 2026-10-12 — Compatibility fix: legacy `max_agents` coercion on `POST /v1/opensearch`

- Restored the pre-#163 behavior of `max_agents`: numeric strings (e.g. `"5"`), integral floats and booleans are accepted again, as they were before #163. The change in #163 had rejected them, which broke existing clients of a legacy route.
- The OpenAPI schema keeps the preferred JSON integer form (1..100) and now describes the legacy coercion.
- Schemathesis excludes only `negative_data_rejection` for `POST /v1/opensearch`, with the reason versioned in `scripts/run_schemathesis_contract.sh`.

