from fastapi import FastAPI

from ayorai_attractor.audit import AuditReport
from ayorai_attractor.audit_store import AuditTraceStore
from ayorai_attractor.models import (
    AuditFindingResponse,
    AuditResponse,
    AuditTraceResponse,
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
from ayorai_attractor.verification.models import Verdict
from ayorai_attractor.verification.response import ResponseStatus

app = FastAPI(
    title="AYORAI ATTRACTOR",
    version="0.1.0",
    description="Adaptive multi-agent intelligence and verification engine.",
)
engine = Attractor()
audit_store = AuditTraceStore()


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
    audit_store.record(response, report)
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
            traceability=Traceability(adr="ADR-002", rules=["§5"]),
        )

    judgments, verdict = judge(request.claims, request.evidence, request.stances)
    status = (
        ResponseStatus.ABSTAIN_NO_ANSWER
        if verdict is Verdict.UNVERIFIED
        else ResponseStatus(verdict.value)
    )
    api_verdict = None if status is ResponseStatus.ABSTAIN_NO_ANSWER else verdict
    return VerificationAPIResponse(
        status=status,
        verdict=api_verdict,
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


@app.get("/v1/audit/{trace_id}", response_model=AuditTraceResponse)
def audit_trace(trace_id: str) -> AuditTraceResponse:
    """Return persisted audit metadata without exposing raw evidence or prompts."""
    saved = audit_store.get(trace_id)
    if saved is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="audit trace not found")
    return AuditTraceResponse(**saved)
