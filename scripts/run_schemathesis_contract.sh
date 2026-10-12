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
# positive_data_acceptance.
"$ST_BIN" run "$OPENAPI_URL" --url "$API_URL" --checks all \
  --exclude-path '^/v1/verify$'

"$ST_BIN" run "$OPENAPI_URL" --url "$API_URL" --checks all \
  --include-path '^/v1/verify$' --include-method POST \
  --exclude-checks positive_data_acceptance
