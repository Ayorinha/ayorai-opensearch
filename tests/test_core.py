from fastapi.testclient import TestClient

from attractor.api.app import app
from attractor.models import SearchRequest, VerificationStatus
from attractor.orchestrator import Attractor


def test_orchestrator_is_unverified_without_external_sources() -> None:
    result = Attractor().run(SearchRequest(query="test query"))
    assert result.verification is VerificationStatus.UNVERIFIED
    assert "research" in result.agents_used
    assert result.confidence < 0.5


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
    assert payload["verification"] == "unverified"
    assert payload["trace_id"].startswith("tr_")
