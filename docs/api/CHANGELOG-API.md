# API changelog

All public API contract changes are additive unless explicitly identified otherwise.

## Unreleased — `/v2/audit` traces bind the returned adjudication (`r2-v4`, additive)

- **Fix:** the `/v2/audit` trace was recorded before adjudication and held only retrieval counts, so it could not show which verdicts were returned. It is now recorded after adjudication as `replay_version` `r2-v4` (store schema 4).
- New response field `AuditV2Response.adjudication_sha256`: SHA-256 of the RFC 8785 (JCS) encoding of `{check_trace_id, claims_source, engine, documents, results}` of the response body. A client recomputes it from the body it received.
- New optional fields on `GET /v1/audit/{trace_id}`: `check_trace_id` and `adjudication_sha256`, set only on `r2-v4` traces. The `r2-v4` replay digest and HMAC cover every `r2-v3` field plus these two. A value attached to an `r2-v1`/`r2-v2`/`r2-v3` trace makes it `invalid`.
- `replay_version` gains the value `r2-v4`. `/v1/audit` traces stay `r2-v3`. The SQLite store adds two nullable columns in place; existing traces and their digests are unchanged. The trace still holds digests, not the claims or excerpts themselves.

## Unreleased — `POST /v2/audit` (additive)

- New end-to-end route: search, then adjudicate claims with the ADR-002 Judge against the independent sources retrieved for the query. Claims come from the caller (`claims`), from a caller answer (`answer`), or by default from the engine's own answer. Model-generated text is never used as evidence; without an independent source every claim abstains with `no_independent_source`.
- The run is recorded as an audit trace owned by the calling key (`trace_id`, readable through `GET /v1/audit/{trace_id}`); `check_trace_id` is the digest of the claim check. (As first released, the trace held only retrieval counts; see the `r2-v4` entry above.)
- `/v2/audit` is subject to authentication, the body limit and `ATTRACTOR_MAX_INFLIGHT_HEAVY`, like the `/v1` POST routes. No existing route, request or response changed.

## Unreleased — `/v1/check` rule detector v10 (non-assertive framing and bounds)

- A sentence that states the claim only as a possibility, estimate, projection, rumour, hypothesis or open question ("pode ter sido", "estima-se que", "rumores indicam", "deve atingir… segundo projeções", "se fosse", "não se sabe se", "reportedly") is now `neutral` for it. Previously it supported the claim, and "não se sabe se P" refuted it. Affirmative legal and technical wording ("previsto no", "deverá", "não pode ter duração superior a") is not treated as a hedge.
- In evidence, a number introduced by a bound ("superou 40", "abaixo de 40", "mais de 40", "at least 40") no longer confirms or contradicts an exact claimed value; bounded claims still compare with bounded evidence.
- The component version is now `10`. Golden v0 and v0.1 predictions are unchanged. No request or response field changed.

## Unreleased — `/v1/check` rule detector v9 (decision fixes)

- A negator in a sentence that does not state the claim no longer turns a confirming sentence into a contradiction: "A Vértice não faliu. A receita foi de 40 milhões em 2024." now supports a claim about the revenue. A sentence made only of denial words ("Isso não é verdade.", "Não procede.") still denies the previous one. Single-sentence excerpts are classified exactly as before.
- A reported denial ("X negou que P", "desmentiu que", "contesta que", "denied that") is `neutral` for P: the document neither asserts P nor establishes that P is false. Previously it supported P.
- The component version in `components` is now `9`. Golden v0 and v0.1 predictions are unchanged. No request or response field changed.

## Unreleased — audit traces: ownership, schema v3 and `r2-v3` (behavior change)

- **Behavior change:** `GET /v1/audit/{trace_id}` returns a trace only to the API key that created it. Any other key gets the same 404 body as for an unknown trace. Response schemas are unchanged.
- Traces recorded before schema v3 have no owner and are hidden from every key by default. `ATTRACTOR_AUDIT_LEGACY_TRACES=shared` restores the previous visibility for them; any other value prevents startup.
- New traces report `replay_version` `r2-v3`: the digest covers every persisted field, including owner, `recorded_at` (UTC) and `software_version`. `r2-v2` traces keep verifying under the previous rule. The SQLite store migrates from schema 2 to 3 in place, idempotently.
- Optional `ATTRACTOR_AUDIT_HMAC_KEYS` adds an HMAC-SHA-256 per trace; a missing or altered MAC makes `replay_integrity` `invalid`.
- The `trace_id` values of `/v1/check` (`chk_…`) and `/v1/fields` (`fld_…`) are content digests and are not stored; `GET /v1/audit/{trace_id}` returns 404 for them, as before.

## Unreleased — host-wide admission limit (opt-in)

- `ATTRACTOR_INFLIGHT_SCOPE=host` shares the `ATTRACTOR_MAX_INFLIGHT_HEAVY` limit across all workers on the same host. The default (`process`) is unchanged. No request or response body changed.

## Unreleased — admission control for verification routes

- `POST /v1/check`, `/v1/fields`, `/v1/verify`, `/v1/audit` and `/v1/opensearch` now return **HTTP 503** with `Retry-After: 1` when more than `ATTRACTOR_MAX_INFLIGHT_HEAVY` (default 2) such requests are already running in the same worker process. The 503 response is documented in the OpenAPI document.
- Measured on one worker with 16 clients sending 2 MB `/v1/check` bodies: p99 34.1 s → 3.3 s and peak RSS 1696 MB → 277 MB, with accepted throughput 0.47 → 0.57 requests/s. Clients should retry after `Retry-After`.
- No request or response body changed. `GET /health` and `GET /v1/audit/{trace_id}` are not limited.

## Unreleased — documented error responses match the implementation

- The OpenAPI document no longer lists HTTP 400 on any route. No route returns 400: a body that is not valid JSON returns 422 with `type` `json_invalid`, as it already did.
- A JSON body that is not valid UTF-8 now also returns 422 `json_invalid` (it returned 400 `There was an error parsing the body`). JSON text must be UTF-8 (RFC 8259, section 8.1).
- Every `/v1/*` route now documents HTTP 401 (missing or invalid API key when `ATTRACTOR_AUTH_MODE=api_key`), and every `POST` route documents HTTP 413 (body above `ATTRACTOR_MAX_BODY_BYTES`). Both responses were already returned; only the document changes.
- No request, response body or status code returned by the API changed.

## 2026-11-14 — `/v1/fields` negative values (field-check-4)

- A minus sign (`-` or `−`) written right before a `number` or `money` value in the document belongs to it: `-5`, `R$ -100,00`, `R$-100,00` and `-R$ 100,00` are negative. Previously the sign was ignored, so an expected `5` matched a document `-5` (false `conforme`).
- A hyphen right after a letter, digit, `.` or `,` is not a sign (`10-12`, `art. 5-A`), and a spaced hyphen is not a sign (`10 - 12`). The sign and the amount must be on the same line as `R$` when `R$` sits between them.
- Two signs in the document (`--5`, `- -5`, `-R$ -100,00`) are ambiguous: the value is not a candidate and the field is `ausente`.
- Expected `money` values may carry the same sign forms; two signs (`-R$ -10,00`) are `invalido`. Negative zero is zero.
- The reported `found`, `start` and `end` include the sign (and the `R$` between the sign and the amount).
- The response engine metadata reports `field-check-4`. No request or response fields were added or removed.

## 2026-11-14 — `/v1/fields` strict digits (field-check-3)

- Expected `number` values must be plain decimals written with ASCII digits (optional sign, `.` or `,` as the decimal mark). `NaN`, `Infinity`, exponents (`1e3`), underscores (`1_000`) and non-ASCII digits now return `invalido` instead of being normalised.
- Expected `money`, `date` and `cpf_cnpj` values with non-ASCII digits (for example full-width `１２`) return `invalido`; an expected CPF/CNPJ may contain only ASCII digits, `.`, `/`, `-` and spaces.
- Document values written with non-ASCII digits are no longer candidates, so the field is `ausente` (abstention) rather than compared through a look-alike value. An ASCII run touching a non-ASCII digit (`１２3`) is not read as a shorter number (`3`).
- A `number` is never taken as the prefix of a longer dotted or comma sequence (`1.2.3`, `1.000.000`, `1,5.2`); previously `1.2` or `1.000` was extracted from such a sequence. The field is `ausente` instead.
- The response engine metadata reports `field-check-3`. No request or response fields were added or removed.

## 2026-11-11 — `/v1/fields` trace identity v2 (semantics clarified)

- The deterministic `trace_id` now binds the caller document ID, media type, extracted-text SHA-256, original-source SHA-256 and page boundaries, in addition to the submitted field specification.
- Changing the source file or page layout therefore produces a different trace ID even when extracted text is identical. This prevents distinct source/evidence provenance from sharing one trace identifier.
- The response engine metadata identifies this format as `fields-trace-2`.
- No request or response fields were added or removed; consumers should treat `trace_id` as an opaque identifier and must not assume IDs remain equal across the previous trace format.
- `trace_id` is a provenance/diagnostic identifier, not a business key, authorization token or digital signature; consumers should not use it as a substitute for document identity or evidence verification.

## 2026-11-08 — /v1/fields and /v1/check hardening (field-check-2, document-check-2)

- `/v1/fields`: new outcome `ambiguo` when one label introduces different values; a value
  belongs to the nearest preceding label (same line or the line above); a text field
  with labels is compared with the whole value the label introduces (no fragments, no
  match under another label); `R$` amounts without cents are recognised.
- `/v1/check`: quoted text and passages addressed to the checker (embedded
  instructions) never count as support.

## 2026-11-08 — POST /v1/fields

- New endpoint: compares submitted field values (money, date, CPF/CNPJ, number, text)
  with one document (text or PDF). Outcomes: `conforme`, `divergente` (with the document
  value, offsets, page and excerpt), `ausente` (abstention) or `invalido` (malformed
  expected value, e.g. wrong CPF/CNPJ check digits). Labels match whole words only.

## 2026-11-08 — POST /v1/check (additive)

- New endpoint `POST /v1/check` (schema `c1`): checks caller-supplied `claims`, or an `answer` decomposed into claims, against caller-supplied `documents` (1–20, up to 200,000 characters each).
- Per claim: Judge verdict (ADR-002) or abstention, with evidence passages carrying exact character offsets and stance (`supports`, `contradicts`, `neutral`).
- Response includes `trace_id` (deterministic and bound to the original source SHA-256 as well as extracted text), SHA-256 and length of each document, and the version of every component (claim extractor, passage selection, stance detector, Judge).
- Support is conservative: a passage supports a claim only if it contains at least 80% of the claim's content words and every number in the claim; contradictions are never weakened. Absent support yields `abstain/no_answer`, never an inferred verdict.
- Documents may be sent as `text` or as `content_base64` with `media_type` (`text/plain` or `application/pdf`). PDFs need a text layer (optional dependency `pypdf`, extra `documents`); a PDF without extractable text is rejected with HTTP 422 and an explicit message (OCR not supported). Evidence carries the 1-based `page`; each document digest carries `media_type`, `pages` and `source_sha256` (hash of the uploaded bytes).
- Additive only: no existing request schema, response schema, status code or Judge rule changed.

## 2026-11-04 — Failure stage diagnostics (additive)

- Added the optional, nullable `stage` field to `Failure` (in `SearchResponse.failures`) and to `AuditFindingResponse` (in `POST /v1/audit` findings). Allowed values: `retrieval`, `extraction`, `nli`, `judge` (schema `FailureStage`).
- `stage` is `null` when the failing step is not identified. `message` is unchanged: the stage is never embedded in the message text.
- Additive response change only: no request schema, status code, Judge rule, Golden artifact or threshold changes. Clients that ignore unknown fields are unaffected.
- Scope: retrieval failures are tagged in the orchestrator and research agent; `ClaimVerificationResult.failure_stage` (library, not HTTP) tags extraction, NLI and Judge processing errors that already resolve to `ABSTAIN_PROCESSING_ERROR`.

## 2026-10-23 — Preparação da versão global 0.6.0: autenticação obrigatória por padrão (mudança incompatível)

- **Comportamento padrão:** a aplicação inicia com `ATTRACTOR_AUTH_MODE=api_key`; se o material de chave exigido estiver ausente ou malformado, a inicialização falha fechada. Implantações que antes dependiam do modo sem autenticação devem configurar uma chave antes de atualizar.
- **Envio da chave:** use `Authorization: Bearer <chave>` ou `X-API-Key: <chave>`, conforme a integração. `/health` continua público; as demais rotas protegidas exigem autenticação.
- **Desenvolvimento isolado:** `ATTRACTOR_AUTH_MODE=off` deve ser definido explicitamente e não deve ser usado como configuração padrão de implantação.
- **Migração:** consulte o [guia de autenticação](../security/API-AUTH.md). Provisionar `ATTRACTOR_API_KEY_PEPPER` (segredo de 32 bytes em 64 caracteres hexadecimais) e `ATTRACTOR_API_KEYS_HMAC_SHA256` (lista separada por vírgulas de digests HMAC-SHA-256 de 64 caracteres hexadecimais), além de configurar os clientes e validar chamadas autenticadas antes de promover a versão. Nunca registrar chaves, pepper ou cabeçalhos de autorização em logs.
- Esta nota descreve a linha global do produto `0.6.0`; não muda a versão separada do executor RGC (`rgc-eval/0.7.0`) nem afirma que a release global já foi publicada.

## 2026-10-17 — Fix #250: Schemathesis legacy `max_agents` checks on `/v1/audit`

- Fixed the Schemathesis contract-test configuration: `POST /v1/audit` shares `SearchRequest` with `POST /v1/opensearch`, so both routes intentionally retain legacy `max_agents` coercion (numeric strings, integral floats and booleans) restored in #169.
- The general Schemathesis run now excludes both routes, and the dedicated run includes both while excluding only `negative_data_rejection`. All other checks, including `positive_data_acceptance`, remain enabled for both routes.
- This is a test-configuration correction, not an API behavior change. OpenAPI and `SearchRequest` are unchanged.

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
