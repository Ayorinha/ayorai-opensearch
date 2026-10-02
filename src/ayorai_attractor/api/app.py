from fastapi import FastAPI

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.models import SearchRequest, SearchResponse
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.verification.judge import judge
from ayorai_attractor.verification.models import (
    ClaimJudgmentResponse,
    VerificationRequest,
    VerificationResponse,
)

app = FastAPI(
    title="AYORAI ATTRACTOR",
    version="0.1.0",
    description="Adaptive multi-agent intelligence and verification engine.",
)
engine = Attractor()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ayorai-attractor"}


@app.post("/v1/opensearch", response_model=SearchResponse)
def opensearch(request: SearchRequest) -> SearchResponse:
    return engine.run(request)


@app.post("/v1/opensearch/audit", response_model=AuditReport)
def opensearch_audit(request: SearchRequest) -> AuditReport:
    """Run the same verification flow and expose its deterministic audit record."""
    response = engine.run(request)
    return AuditReport.from_response(response)


@app.post("/v1/verify", response_model=VerificationResponse)
def verify(request: VerificationRequest) -> VerificationResponse:
    """Evaluate structured claims and evidence with the deterministic R1 Judge."""
    judgments, verdict = judge(request.claims, request.evidence, request.stances)
    return VerificationResponse(
        judgments=[
            ClaimJudgmentResponse(
                claim_id=item.claim_id,
                support_clusters=item.support_clusters,
                contradiction_clusters=item.contradiction_clusters,
                provenance_complete=item.provenance_complete,
                verdict=item.verdict,
            )
            for item in judgments
        ],
        verdict=verdict,
    )
