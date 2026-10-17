#!/usr/bin/env bash
set -euo pipefail

ST_BIN="${1:?path to the pinned Schemathesis executable required}"
OPENAPI_URL="${2:?OpenAPI URL required}"
API_URL="${3:?API URL required}"
REPORT_DIR="${4:-schemathesis-report}"
# Fixed seed: the same inputs are generated on every run, so a failure is
# reproducible from the logged seed instead of appearing at random. Override
# with SCHEMATHESIS_SEED to explore other inputs deliberately.
SEED="${SCHEMATHESIS_SEED:-20261003}"
echo "Schemathesis seed: ${SEED}; reports: ${REPORT_DIR}"
COMMON=(--checks all --seed "$SEED" --report junit,ndjson)

# The r1-a Evidence model enforces end_offset > start_offset across two fields.
# JSON Schema cannot express this relational invariant. Keep the invariant in
# application validation and exclude only positive_data_acceptance for POST
# /v1/verify; all other Schemathesis checks remain enabled for that operation.
# Every other operation still runs the complete --checks all set, including
# positive_data_acceptance. Path filters are used alone: combined with
# --include-method they are OR-ed and would widen the selection to every POST
# operation.
# Legacy /v1/opensearch keeps Pydantic lax integer coercion for max_agents
# (numeric strings, integral floats and booleans were accepted before v0.5.0).
# The schema documents the preferred JSON integer form, so only
# negative_data_rejection is excluded for that operation; every other check,
# including positive_data_acceptance, still runs for it.
"$ST_BIN" run "$OPENAPI_URL" --url "$API_URL" "${COMMON[@]}" \
  --report-dir "$REPORT_DIR/general" \
  --exclude-path /v1/verify --exclude-path /v1/opensearch

"$ST_BIN" run "$OPENAPI_URL" --url "$API_URL" "${COMMON[@]}" \
  --report-dir "$REPORT_DIR/opensearch" \
  --include-path /v1/opensearch \
  --exclude-checks negative_data_rejection

"$ST_BIN" run "$OPENAPI_URL" --url "$API_URL" "${COMMON[@]}" \
  --report-dir "$REPORT_DIR/verify" \
  --include-path /v1/verify \
  --exclude-checks positive_data_acceptance
