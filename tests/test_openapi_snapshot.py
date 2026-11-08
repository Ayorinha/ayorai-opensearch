import json
from pathlib import Path

from ayorai_attractor.api.app import app


def test_openapi_snapshot_matches_generated_contract() -> None:
    snapshot_path = Path(__file__).resolve().parents[1] / "docs" / "api" / "openapi.json"
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    actual = app.openapi()
    # JSON numeric values such as 0 and 0.0 are semantically equivalent.
    assert actual == expected


def test_protected_routes_document_rate_limit_response() -> None:
    schema = app.openapi()
    protected_operations = (
        schema["paths"]["/v1/opensearch"]["post"],
        schema["paths"]["/v1/audit"]["post"],
        schema["paths"]["/v1/verify"]["post"],
        schema["paths"]["/v1/check"]["post"],
        schema["paths"]["/v1/audit/{trace_id}"]["get"],
    )

    for operation in protected_operations:
        response = operation["responses"]["429"]
        assert response["description"] == "The request rate limit was exceeded."
        retry_after = response["headers"]["Retry-After"]
        assert retry_after["schema"]["type"] == "integer"
        assert retry_after["schema"]["minimum"] == 1
        detail_schema = response["content"]["application/json"]["schema"]["properties"]["detail"]
        assert detail_schema["type"] == "string"

    assert "429" not in schema["paths"]["/health"]["get"]["responses"]
