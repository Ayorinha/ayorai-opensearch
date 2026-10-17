import json
from pathlib import Path

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from ayorai_attractor.api.app import app
from ayorai_attractor.models import SearchRequest


def test_search_request_preserves_legacy_integer_boolean_coercion() -> None:
    zero = SearchRequest(query="valid query", require_primary_source=0)
    one = SearchRequest(query="valid query", require_primary_source=1)
    assert zero.require_primary_source is False
    assert one.require_primary_source is True


def test_opensearch_preserves_legacy_max_agents_coercion() -> None:
    """Legacy /v1/opensearch accepted lax integer forms before #163; keep them."""
    client = TestClient(app)
    for value in (5, 5.0, "5", True):
        response = client.post(
            "/v1/opensearch",
            json={"query": "valid query", "max_agents": value},
        )
        assert response.status_code == 200, value

    for value in ("abc", 5.5, 0, 101):
        response = client.post(
            "/v1/opensearch",
            json={"query": "valid query", "max_agents": value},
        )
        assert response.status_code == 422, value


def test_verify_returns_deterministic_verified_result() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/verify",
        json={
            "schema_version": "r1-a",
            "claims": [{"id": "c1", "text": "The service launched in 2026."}],
            "evidence": [
                {
                    "id": "e1",
                    "claim_id": "c1",
                    "source_id": "source-a",
                    "source_location": "document:1",
                    "retrieved_at": "2026-10-02T09:00:00Z",
                    "start_offset": 0,
                    "end_offset": 30,
                    "excerpt": "The service launched in 2026.",
                    "origin_id": "origin-a",
                },
                {
                    "id": "e2",
                    "claim_id": "c1",
                    "source_id": "source-b",
                    "source_location": "document:2",
                    "retrieved_at": "2026-10-02T09:00:01Z",
                    "start_offset": 0,
                    "end_offset": 30,
                    "excerpt": "The service launched in 2026.",
                    "origin_id": "origin-b",
                },
            ],
            "stances": [
                {
                    "id": "s1",
                    "claim_id": "c1",
                    "evidence_id": "e1",
                    "stance": "supports",
                },
                {
                    "id": "s2",
                    "claim_id": "c1",
                    "evidence_id": "e2",
                    "stance": "supports",
                },
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "r1-a",
        "status": "verified",
        "verdict": "verified",
        "judgments": [
            {
                "claim_id": "c1",
                "support_clusters": 2,
                "contradiction_clusters": 0,
                "provenance_complete": True,
                "verdict": "verified",
            }
        ],
        "traceability": {
            "adr": "ADR-002",
            "rules": ["§1", "§2", "§3", "§4", "§5", "§9"],
        },
    }


def test_verify_abstains_when_claim_is_unverified() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/verify",
        json={
            "schema_version": "r1-a",
            "claims": [{"id": "c1", "text": "Unknown claim."}],
            "evidence": [],
            "stances": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "abstain/no_answer"
    assert response.json()["verdict"] is None
    assert response.json()["judgments"][0]["verdict"] == "unverified"


def test_verify_rejects_extra_fields_and_invalid_schema_version() -> None:
    client = TestClient(app)

    extra = client.post(
        "/v1/verify",
        json={
            "schema_version": "r1-a",
            "claims": [{"id": "c1", "text": "Unknown claim."}],
            "unexpected": True,
        },
    )
    invalid_version = client.post(
        "/v1/verify",
        json={
            "schema_version": "r2",
            "claims": [{"id": "c1", "text": "Unknown claim."}],
        },
    )

    assert extra.status_code == 422
    assert invalid_version.status_code == 422


def test_r1_a_response_bytes_match_pre_policy_baseline() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "r1-a-response-baseline.json"
    baseline = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert baseline["protocol"] == "r1-a"

    client = TestClient(app)
    for case in baseline["cases"]:
        response = client.post("/v1/verify", json=case["request"])
        assert response.status_code == case["expected_status_code"], case["name"]
        assert response.headers["content-type"] == case["expected_content_type"], case["name"]
        assert response.content.decode("utf-8") == case["expected_body"], case["name"]

    for case in baseline["invalid_requests"]:
        response = client.post("/v1/verify", json=case["request"])
        assert response.status_code == case["expected_status_code"], case["name"]
        assert response.headers["content-type"] == case["expected_content_type"], case["name"]
        assert response.content.decode("utf-8") == case["expected_body"], case["name"]


def test_r1_a_duplicate_claim_ids_return_structured_422() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/verify",
        json={
            "schema_version": "r1-a",
            "claims": [
                {"id": "c1", "text": "Claim one."},
                {"id": "c1", "text": "Duplicate claim."},
            ],
            "evidence": [],
            "stances": [],
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "DUPLICATE_ID",
                "loc": ["body", "claims"],
                "msg": "claim ids must be unique",
            }
        ]
    }


def test_r1_a_stance_for_nonexistent_claim_returns_structured_422() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/verify",
        json={
            "schema_version": "r1-a",
            "claims": [{"id": "c1", "text": "Claim one."}],
            "evidence": [],
            "stances": [
                {
                    "id": "s1",
                    "claim_id": "missing-claim",
                    "evidence_id": "e1",
                    "stance": "supports",
                }
            ],
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "DANGLING_REFERENCE",
                "loc": ["body", "stances"],
                "msg": "stance references unknown claim",
            }
        ]
    }


def r1_a_schema_valid_request() -> st.SearchStrategy[dict[str, object]]:
    claim_ids = st.sampled_from(["c1", "c2", "c3"])
    evidence_ids = st.sampled_from(["e1", "e2", "e3"])
    claim = st.fixed_dictionaries(
        {
            "id": claim_ids,
            "text": st.sampled_from(["Claim one.", "Claim two.", "Claim three."]),
        }
    )
    evidence = st.fixed_dictionaries(
        {
            "id": evidence_ids,
            "claim_id": claim_ids,
            "source_id": st.sampled_from(["source-a", "source-b"]),
            "source_location": st.sampled_from(["document:1", "document:2"]),
            "retrieved_at": st.just("2026-10-02T09:00:00Z"),
            "start_offset": st.just(0),
            "end_offset": st.just(3),
            "excerpt": st.just("abc"),
            "origin_id": st.sampled_from(["origin-a", "origin-b"]),
        }
    )
    stance = st.fixed_dictionaries(
        {
            "id": st.sampled_from(["s1", "s2", "s3"]),
            "claim_id": claim_ids,
            "evidence_id": evidence_ids,
            "stance": st.sampled_from(["supports", "contradicts", "neutral"]),
        }
    )
    return st.fixed_dictionaries(
        {
            "schema_version": st.just("r1-a"),
            "claims": st.lists(claim, min_size=1, max_size=3),
            "evidence": st.lists(evidence, max_size=4),
            "stances": st.lists(stance, max_size=5),
        }
    )


@given(request=r1_a_schema_valid_request())
@settings(max_examples=250, deadline=None)
def test_r1_a_schema_valid_inputs_never_return_http_500(
    request: dict[str, object],
) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/v1/verify", json=request)
    assert response.status_code != 500
    assert response.status_code in {200, 422}


def test_r1_a_unexpected_value_error_from_judge_remains_http_500(monkeypatch) -> None:
    import importlib

    api_module = importlib.import_module("ayorai_attractor.api.app")

    def unexpected_failure(*args, **kwargs):
        raise ValueError("unexpected internal programming error")

    monkeypatch.setattr(api_module, "judge", unexpected_failure)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/v1/verify",
        json={
            "schema_version": "r1-a",
            "claims": [{"id": "c1", "text": "A valid claim."}],
            "evidence": [],
            "stances": [],
        },
    )

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def r2_a_request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "r2-a",
        "protocol_version": "r2-a",
        "claim_id": "c1",
        "claim_text": "Claim A",
        "atoms": [{"id": "a1", "text": "Claim A", "start_offset": 0, "end_offset": 7}],
        "evidence": [
            {
                "id": "e1",
                "claim_id": "c1",
                "source_id": "source-e1",
                "source_location": "document:1",
                "retrieved_at": "2026-10-11T12:00:00Z",
                "start_offset": 0,
                "end_offset": 7,
                "excerpt": "Claim A",
                "origin_id": "origin-e1",
            }
        ],
        "stances": [{"id": "s1", "atom_id": "a1", "evidence_id": "e1", "stance": "SUPPORTS"}],
        "source_texts": {"source-e1": "Claim A"},
    }
    payload.update(overrides)
    return payload


def test_r2_a_returns_complete_canonical_decided_result() -> None:
    response = TestClient(app).post("/v1/verify", json=r2_a_request())

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "r2-a"
    assert body["result"]["judge_rules_version"] == "2.0.0"
    assert body["result"]["decision_state"] == "DECIDED"
    assert body["result"]["verdict"] == "SUPPORTED"
    assert len(body["result"]["output_sha256"]) == 64
    assert body["response_policy"] is None


def test_r2_a_returns_abstained_without_factual_verdict() -> None:
    response = TestClient(app).post("/v1/verify", json=r2_a_request(out_of_scope=True))

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["decision_state"] == "ABSTAINED"
    assert result["verdict"] is None
    assert response.json()["response_policy"] == "abstain/out_of_scope"


def test_r2_a_returns_invalid_input_as_canonical_result() -> None:
    response = TestClient(app).post("/v1/verify", json=r2_a_request(atoms=[]))

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["decision_state"] == "INVALID_INPUT"
    assert result["verdict"] is None
    assert result["reason_codes"] == ["NO_ATOMS"]
    assert len(result["output_sha256"]) == 64


def test_r2_a_unverified_remains_decided_with_separate_response_policy() -> None:
    response = TestClient(app).post(
        "/v1/verify",
        json=r2_a_request(evidence=[], stances=[], source_texts={}),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["decision_state"] == "DECIDED"
    assert body["result"]["verdict"] == "UNVERIFIED"
    assert body["response_policy"] is None


def test_unknown_schema_version_returns_structured_http_422() -> None:
    response = TestClient(app).post(
        "/v1/verify",
        json={"schema_version": "r9", "claims": [{"id": "c1", "text": "Claim."}]},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == [
        {
            "type": "literal_error",
            "loc": ["body", "schema_version"],
            "msg": "Input should be 'r1-a'",
            "input": "r9",
            "ctx": {"expected": "'r1-a'"},
        }
    ]


def test_r1_a_error_responses_match_pre_r2_a_baseline_byte_for_byte() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "r1-a-error-baseline.json"
    baseline = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert baseline["captured_from"] == "c7e3868f3f6f34ce153d9ec6605645fad8681e2e"

    client = TestClient(app, raise_server_exceptions=False)
    for case in baseline["cases"]:
        response = client.post(
            "/v1/verify",
            content=case["request"].encode("utf-8"),
            headers={"content-type": "application/json"},
        )
        assert response.status_code == case["status"], case["name"]
        assert response.content.decode("utf-8") == case["body"], case["name"]


def test_openapi_documents_both_verify_request_contracts() -> None:
    schema = TestClient(app).get("/openapi.json").json()
    request_schema = schema["paths"]["/v1/verify"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    expected_refs = {
        "#/components/schemas/VerificationRequest",
        "#/components/schemas/Judge2VerificationRequest",
    }
    assert {item["$ref"] for item in request_schema["oneOf"]} == expected_refs
    assert expected_refs <= {
        f"#/components/schemas/{name}" for name in schema["components"]["schemas"]
    }


def test_r2_a_response_matches_declared_response_model_and_openapi_statuses() -> None:
    from ayorai_attractor.verification.api_models import Judge2VerificationResponse

    response = TestClient(app).post("/v1/verify", json=r2_a_request())
    assert response.status_code == 200
    Judge2VerificationResponse.model_validate(response.json())

    schema = app.openapi()
    verify_responses = schema["paths"]["/v1/verify"]["post"]["responses"]
    assert "200" in verify_responses
    assert "422" in verify_responses
    response_schema = verify_responses["200"]["content"]["application/json"]["schema"]
    assert response_schema["oneOf"] == [
        {"$ref": "#/components/schemas/VerificationAPIResponse"},
        {"$ref": "#/components/schemas/Judge2VerificationResponse"},
    ]
    assert "404" in schema["paths"]["/v1/audit/{trace_id}"]["get"]["responses"]
    assert "422" in schema["paths"]["/v1/audit/{trace_id}"]["get"]["responses"]
    assert "422" in schema["paths"]["/v1/audit"]["post"]["responses"]


def test_r2_a_rejects_unknown_nested_atom_and_stance_fields() -> None:
    client = TestClient(app)
    bad_atom = r2_a_request()
    bad_atom["atoms"] = [
        {"id": "a1", "text": "Claim A", "start_offset": 0, "end_offset": 7, "unexpected": True}
    ]
    bad_stance = r2_a_request()
    bad_stance["stances"] = [
        {"id": "s1", "atom_id": "a1", "evidence_id": "e1", "stance": "SUPPORTS", "unexpected": True}
    ]

    assert client.post("/v1/verify", json=bad_atom).status_code == 422
    assert client.post("/v1/verify", json=bad_stance).status_code == 422


def test_openapi_documents_r1_a_stance_requires_evidence() -> None:
    schema = app.openapi()["components"]["schemas"]["VerificationRequest"]
    assert schema["not"] == {
        "type": "object",
        "properties": {
            "evidence": {"maxItems": 0},
            "stances": {"minItems": 1},
        },
        "required": ["stances"],
    }


def test_r2_a_accepts_safe_integer_boundary_without_server_error() -> None:
    safe_max = 2**53 - 1
    payload = r2_a_request()
    payload["atoms"] = [
        {"id": "a1", "text": "Claim A", "start_offset": safe_max - 1, "end_offset": safe_max}
    ]
    payload["evidence"] = [
        {
            "id": "e1",
            "claim_id": "c1",
            "source_id": "source-e1",
            "source_location": "document:1",
            "retrieved_at": "2026-10-11T12:00:00Z",
            "start_offset": safe_max - 1,
            "end_offset": safe_max,
            "excerpt": "Claim A",
            "origin_id": "origin-e1",
        }
    ]
    response = TestClient(app).post("/v1/verify", json=payload)
    assert response.status_code != 422
    assert response.status_code < 500


def test_r2_a_rejects_integers_outside_rfc8785_safe_range() -> None:
    client = TestClient(app)
    for value in (2**53, 2**53 + 1, 2**60, -(2**53), -(2**53 + 1), -(2**60)):
        bad_atom = r2_a_request()
        bad_atom["atoms"] = [
            {"id": "a1", "text": "Claim A", "start_offset": value, "end_offset": 7}
        ]
        assert client.post("/v1/verify", json=bad_atom).status_code == 422

        bad_evidence = r2_a_request()
        bad_evidence["evidence"] = [
            {
                "id": "e1",
                "claim_id": "c1",
                "source_id": "source-e1",
                "source_location": "document:1",
                "retrieved_at": "2026-10-11T12:00:00Z",
                "start_offset": 0,
                "end_offset": value,
                "excerpt": "Claim A",
                "origin_id": "origin-e1",
            }
        ]
        assert client.post("/v1/verify", json=bad_evidence).status_code == 422


def test_r2_a_response_explanations_are_canonical_and_do_not_change_verdict() -> None:
    from ayorai_attractor.verification.judge2 import verify_output

    response = TestClient(app).post("/v1/verify", json=r2_a_request())
    assert response.status_code == 200
    body = response.json()
    result = body["result"]
    assert verify_output(result)
    assert body["technical_explanation"] == result
    assert len(body["simple_explanation"]) <= 5
    assert f"Veredito determinístico: {result['verdict']}." in body["simple_explanation"]


def test_r2_a_abstained_and_invalid_input_explanations_never_emit_verdict() -> None:
    client = TestClient(app)
    for payload, expected_state in (
        (r2_a_request(out_of_scope=True), "ABSTAINED"),
        (r2_a_request(atoms=[]), "INVALID_INPUT"),
    ):
        response = client.post("/v1/verify", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["result"]["decision_state"] == expected_state
        assert body["result"]["verdict"] is None
        assert body["technical_explanation"] == body["result"]
        assert any("nenhum veredito factual" in line for line in body["simple_explanation"])
