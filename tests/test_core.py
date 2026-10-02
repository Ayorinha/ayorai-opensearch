from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
from ayorai_attractor.models import SearchRequest, VerificationStatus
from ayorai_attractor.orchestrator import Attractor


def test_orchestrator_abstains_without_verified_evidence() -> None:
    result = Attractor().run(SearchRequest(query="test query"))
    assert result.verification is VerificationStatus.INSUFFICIENT_EVIDENCE
    assert "research" in result.agents_used
    assert result.confidence == 0.0
    assert result.answer.startswith("Abstained:")


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_opensearch() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/opensearch",
        json={"query": "compare RAG and fine-tuning", "mode": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["verification"] == "insufficient_evidence"
    assert payload["confidence"] == 0.0
    assert payload["answer"].startswith("Abstained:")
    assert payload["trace_id"].startswith("tr_")


def test_opensearch_audit() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/opensearch/audit",
        json={"query": "compare RAG and fine-tuning", "mode": "balanced"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["verification"] == "insufficient_evidence"
    assert payload["trace_id"].startswith("tr_")
    assert payload["evidence_count"] == 1
    assert payload["independent_evidence_count"] == 1
    assert payload["verified_evidence_count"] == 0
    assert [item["code"] for item in payload["findings"]] == [
        "NO_EVIDENCE",
        "NO_VERIFIED_EVIDENCE",
        "NON_VERIFIED_RESPONSE",
    ]


def test_structured_r1_verify_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/verify",
        json={
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
    payload = response.json()
    assert payload["verdict"] == "verified"
    assert payload["judgments"] == [
        {
            "claim_id": "c1",
            "support_clusters": 2,
            "contradiction_clusters": 0,
            "provenance_complete": True,
            "verdict": "verified",
        }
    ]
