from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
from ayorai_attractor.models import SearchRequest
from ayorai_attractor.orchestrator import Attractor


def test_orchestrator_is_unverified_without_external_sources() -> None:
    result = Attractor().run(SearchRequest(query="test query"))
    assert result.verification is None
    assert result.verdict_authority == "not_adjudicated"
    assert result.formal_verification_endpoint == "/v1/verify"
    assert result.operation_status in {"completed", "failed"}
    assert "No factual verdict was adjudicated" in result.answer


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
    assert payload["verification"] is None
    assert payload["verdict_authority"] == "not_adjudicated"
    assert payload["formal_verification_endpoint"] == "/v1/verify"
    assert payload["operation_status"] in {"completed", "failed"}
    assert payload["trace_id"].startswith("tr_")
