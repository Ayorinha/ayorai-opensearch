from datetime import UTC, datetime

from ayorai_attractor.verification.extraction import (
    ComponentProvenance,
    ExtractedClaim,
)
from ayorai_attractor.verification.models import Claim, Evidence, Stance
from ayorai_attractor.verification.stance import RuleStanceDetector

def extracted(text: str) -> ExtractedClaim:
    return ExtractedClaim(
        claim=Claim(id="c1", text=text),
        confidence=1.0,
        provenance=ComponentProvenance("test", "fixture", "1", "in", "out"),
    )

def evidence(text: str) -> Evidence:
    return Evidence(
        id="e1",
        claim_id="c1",
        source_id="doc-001",
        source_location="fixture://doc-001",
        retrieved_at=datetime(2026, 9, 30, tzinfo=UTC),
        start_offset=0,
        end_offset=len(text),
        excerpt=text,
        origin_id="atlasgrid-annual-2025",
    )

def test_doc_001_does_not_contradict_itself() -> None:
    claim = extracted("AtlasGrid reported revenue of USD 120 million for fiscal year 2025.")
    result = RuleStanceDetector().detect(
        [claim],
        [
            evidence(
                "AtlasGrid reported revenue of USD 120 million for fiscal year 2025 "
                "and ended the year with 800 employees."
            )
        ],
    )
    assert result.edges[0].edge.stance is Stance.SUPPORTS

def test_year_and_monetary_value_are_different_numeric_attributes() -> None:
    claim = extracted("AtlasGrid revenue was USD 120 million in 2025.")
    result = RuleStanceDetector().detect([claim], [evidence(
        "AtlasGrid revenue was USD 120 million in fiscal year 2025."
    )])
    assert result.edges[0].edge.stance is Stance.SUPPORTS
