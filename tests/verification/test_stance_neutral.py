from datetime import datetime, timezone

from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.judge import judge
from ayorai_attractor.verification.models import Claim, Evidence, Stance, StanceEdge
from ayorai_attractor.verification.stance import RuleStanceDetector

def extracted(claim_id: str, text: str) -> ExtractedClaim:
    return ExtractedClaim(
        claim=Claim(id=claim_id, text=text),
        confidence=1.0,
        provenance=ComponentProvenance("test", "fixture", "1", "in", "out"),
    )

def evidence(claim_id: str, evidence_id: str, text: str) -> Evidence:
    return Evidence(
        id=evidence_id,
        claim_id=claim_id,
        source_id=evidence_id,
        source_location=f"fixture://{evidence_id}",
        retrieved_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
        start_offset=0,
        end_offset=len(text),
        excerpt=text,
        origin_id=evidence_id,
    )

def test_irrelevant_document_is_neutral() -> None:
    result = RuleStanceDetector().detect(
        [extracted("c1", "AtlasGrid revenue was USD 120 million.")],
        [evidence("c1", "e1", "The weather fixture reports rain in Testville.")],
    )
    assert result.edges[0].edge.stance is Stance.NEUTRAL

def test_neutral_is_ignored_by_judge() -> None:
    claim = Claim(id="c1", text="The claim")
    item = evidence("c1", "e1", "Irrelevant document.")
    edge = StanceEdge(id="s1", claim_id="c1", evidence_id="e1", stance=Stance.NEUTRAL)
    judgments, verdict = judge([claim], [item], [edge])
    assert judgments[0].support_clusters == 0
    assert judgments[0].contradiction_clusters == 0
    assert verdict.value == "unverified"
