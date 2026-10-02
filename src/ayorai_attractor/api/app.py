from fastapi import FastAPI

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.models import (
    AuditFindingResponse,
    AuditResponse,
    SearchRequest,
    SearchResponse,
)
from ayorai_attractor.orchestrator import Attractor

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


@app.post("/v1/audit", response_model=AuditResponse)
def audit(request: SearchRequest) -> AuditResponse:
    """Run the engine and expose a deterministic audit of its evidence."""
    response = engine.run(request)
    report = AuditReport.from_response(response)
    return AuditResponse(
        trace_id=report.trace_id,
        verification=report.verification,
        evidence_count=report.evidence_count,
        independent_evidence_count=report.independent_evidence_count,
        verified_evidence_count=report.verified_evidence_count,
        failure_count=report.failure_count,
        findings=[
            AuditFindingResponse(
                code=item.code,
                severity=item.severity.value,
                message=item.message,
            )
            for item in report.findings
        ],
    )
