from datetime import UTC, datetime

from ayorai_attractor.verification.extraction import (
    ComponentProvenance,
    ExtractedClaim,
)
from ayorai_attractor.verification.models import Claim, Evidence, Stance
from ayorai_attractor.verification.stance import NLIStanceDetector, detect_language


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def classify(
        self, claim_text: str, evidence_text: str
    ) -> dict[str, float | str]:
        self.calls.append((claim_text, evidence_text))
        if "TARGET" in evidence_text:
            return {"stance": "supports", "confidence": 0.9}
        return {"stance": "neutral", "confidence": 0.2}


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
        source_id="s1",
        source_location="fixture://e1",
        retrieved_at=datetime(2026, 10, 3, tzinfo=UTC),
        start_offset=100,
        end_offset=100 + len(text),
        excerpt=text,
        origin_id="o1",
    )


def test_windows_preserve_absolute_offsets() -> None:
    detector = NLIStanceDetector(
        FakeBackend(),
        model="fake",
        version="test",
        window_size=10,
        window_overlap=2,
    )
    item = evidence("01234567TARGET")
    result = detector.detect([extracted("claim")], [item])
    assert result.edges[0].edge.stance is Stance.SUPPORTS
    assert "window=108:114" in result.edges[0].provenance.version


def test_language_detection_is_deterministic() -> None:
    assert detect_language("A receita da empresa foi publicada.") == "pt"
    assert detect_language("The company revenue was published.") == "en"
