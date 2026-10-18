#!/usr/bin/env bash
set -euo pipefail

ST_BIN="${1:?path to the pinned Schemathesis executable required}"
OPENAPI_URL="${2:?OpenAPI URL required}"
API_URL="${3:?API URL required}"

# The r1-a Evidence model enforces end_offset > start_offset across two fields.
# JSON Schema cannot express this relational invariant. Keep the invariant in
# application validation and exclude only positive_data_acceptance for POST
# /v1/verify; all other Schemathesis checks remain enabled for that operation.
# Every other operation still runs the complete --checks all set, including
# positive_data_acceptance. Path filters are used alone: combined with
# --include-method they are OR-ed and would widen the selection to every POST
# operation.
# Legacy /v1/opensearch and /v1/audit share SearchRequest, which intentionally
# preserves Pydantic lax integer coercion for max_agents (numeric strings,
# integral floats and booleans, restored in #169). The schema documents the
# preferred JSON integer form, so only negative_data_rejection is excluded
# for both operations; every other check, including positive_data_acceptance,
# still runs for them.
"$ST_BIN" run "$OPENAPI_URL" --url "$API_URL" --checks all \
  --exclude-path /v1/verify --exclude-path /v1/opensearch --exclude-path /v1/audit

"$ST_BIN" run "$OPENAPI_URL" --url "$API_URL" --checks all \
  --include-path /v1/opensearch --include-path /v1/audit \
  --exclude-checks negative_data_rejection

"$ST_BIN" run "$OPENAPI_URL" --url "$API_URL" --checks all \
  --include-path /v1/verify \
  --exclude-checks positive_data_acceptance
