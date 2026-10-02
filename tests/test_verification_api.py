from fastapi.testclient import TestClient

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
