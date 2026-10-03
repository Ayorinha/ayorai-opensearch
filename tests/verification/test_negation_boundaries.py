from datetime import UTC, datetime
from ayorai_attractor.verification.extraction import (
    ComponentProvenance,
    ExtractedClaim,
)
from ayorai_attractor.verification.models import Claim, Evidence, Stance
from ayorai_attractor.verification.stance import _has_negation, RuleStanceDetector

def extracted(text: str) -> ExtractedClaim:
    return ExtractedClaim(claim=Claim(id="c1", text=text), confidence=1.0, provenance=ComponentProvenance("test","fixture","1","in","out"))

def evidence(text: str) -> Evidence:
    return Evidence(id="e1",claim_id="c1",source_id="e1",source_location="fixture://e1",retrieved_at=datetime(2026,9,30,tzinfo=UTC),start_offset=0,end_offset=len(text),excerpt=text,origin_id="o1")

def test_negation_uses_token_boundaries() -> None:
    assert not _has_negation("O ano foi 2025.")
    assert not _has_negation("O mês de novembro foi auditado.")
    assert not _has_negation("A regra sempre foi aplicada.")
    assert _has_negation("A AtlasGrid não aprovou o rollout.")

def test_doc_001_does_not_contradict_itself_after_negation_fix() -> None:
    result=RuleStanceDetector().detect([extracted("AtlasGrid reported revenue of USD 120 million for fiscal year 2025.")],[evidence("AtlasGrid reported revenue of USD 120 million for fiscal year 2025 and ended the year with 800 employees.")])
    assert result.edges[0].edge.stance is Stance.SUPPORTS
