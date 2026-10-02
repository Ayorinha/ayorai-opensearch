from fastapi.testclient import TestClient

from ayorai_attractor.api import app as api
from ayorai_attractor.models import (
    Evidence,
    QualityMode,
    SearchResponse,
    VerificationStatus,
)


class FakeEngine:
    def run(self, request):  # type: ignore[no-untyped-def]
        return SearchResponse(
            query=request.query,
            mode=QualityMode.BALANCED,
            answer="test",
            verification=VerificationStatus.SUPPORTED,
            confidence=0.9,
            evidence=[
                Evidence(
                    id="e1",
                    claim="claim",
                    source="source-a",
                    excerpt="excerpt",
                    independent=True,
                    verified=True,
                ),
                Evidence(
                    id="e2",
                    claim="claim",
                    source="source-b",
                    excerpt="excerpt",
                    independent=True,
                    verified=False,
                ),
            ],
            failures=[],
            agents_used=["fake"],
            trace_id="tr_api",
        )


def test_audit_endpoint_returns_deterministic_report(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(api, "engine", FakeEngine())
    client = TestClient(api.app)

    response = client.post("/v1/audit", json={"query": "test query"})

    assert response.status_code == 200
    assert response.json() == {
        "trace_id": "tr_api",
        "verification": "supported",
        "evidence_count": 2,
        "independent_evidence_count": 2,
        "verified_evidence_count": 1,
        "failure_count": 0,
        "findings": [],
    }


def test_audit_endpoint_rejects_short_query() -> None:
    client = TestClient(api.app)

    response = client.post("/v1/audit", json={"query": "no"})

    assert response.status_code == 422
