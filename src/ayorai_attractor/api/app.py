from fastapi import FastAPI

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.models import (
    AuditFindingResponse,
    AuditResponse,
    SearchRequest,
    SearchResponse,
)
from ayorai_attractor.orchestrator import Attractor
from ayorai_attractor.verification.api_models import (
    ClaimJudgmentResponse,
    Traceability,
    VerificationAPIResponse,
    VerificationRequest,
)
from ayorai_attractor.verification.judge import judge
from ayorai_attractor.verification.response import ResponseStatus

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


@app.post("/v1/verify", response_model=VerificationAPIResponse)
def verify(request: VerificationRequest) -> VerificationAPIResponse:
    """Evaluate structured claims with the deterministic ADR-002 Judge."""
    if not request.claims:
        return VerificationAPIResponse(
            status=ResponseStatus.ABSTAIN_OUT_OF_SCOPE,
            verdict=None,
            judgments=[],
            traceability=Traceability(adr="ADR-002", rules=["§5"] ),
        )

    judgments, verdict = judge(request.claims, request.evidence, request.stances)
    status = (
        "abstain/no_answer"
        if verdict.value == "unverified"
        else verdict
    )
    return VerificationAPIResponse(
        status=status,
        verdict=None if status is ResponseStatus.ABSTAIN_NO_ANSWER else ResponseStatus(verdict.value),
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
        traceability=Traceability(
            adr="ADR-002",
            rules=["§1", "§2", "§3", "§4", "§5", "§9"],
        ),
    )
