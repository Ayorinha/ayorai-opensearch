import json
from pathlib import Path

from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from ayorai_attractor.api.app import app


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
        "detail": {
            "code": "invalid_verification_input",
            "message": "claim ids must be unique",
        }
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
        "detail": {
            "code": "invalid_verification_input",
            "message": "stance references unknown claim",
        }
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
