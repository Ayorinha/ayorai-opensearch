from datetime import UTC, datetime

from ayorai_attractor.verification.excerpt import locate_excerpt, revalidate_evidence
from ayorai_attractor.verification.judge import judge_claim
from ayorai_attractor.verification.models import Claim, Evidence


def evidence(excerpt: str, *, start: int = 0, end: int = 1) -> Evidence:
    return Evidence(
        id="e1",
        claim_id="c1",
        source_id="doc-1",
        source_location="fixture://doc-1",
        retrieved_at=datetime(2026, 10, 4, tzinfo=UTC),
        start_offset=start,
        end_offset=end,
        excerpt=excerpt,
        origin_id="origin-1",
        canonical_url="https://example.test/doc-1",
    )


def test_forged_excerpt_is_rejected() -> None:
    assert locate_excerpt("AtlasGrid revenue was USD 120 million.", "USD 999 million.") is None


def test_excerpt_from_another_document_is_rejected() -> None:
    assert locate_excerpt("Document A says 120.", "Document B says 130.") is None


def test_number_changed_is_rejected() -> None:
    assert locate_excerpt("Revenue was USD 120 million.", "Revenue was USD 121 million.") is None


def test_difference_only_in_spaces_is_rejected() -> None:
    assert locate_excerpt("Revenue was USD 120 million.", "Revenue was USD  120 million.") is None


def test_empty_source_is_rejected() -> None:
    assert locate_excerpt("", "anything") is None


def test_excerpt_longer_than_source_is_rejected() -> None:
    assert locate_excerpt("short", "shorter") is None


def test_valid_excerpt_corrects_supplied_offsets() -> None:
    item = evidence("USD 120 million.", start=99, end=115)
    checked = revalidate_evidence(item, "AtlasGrid revenue was USD 120 million.")
    assert checked is not None
    assert checked.start_offset == 22
    assert checked.end_offset == 38


def test_forged_only_evidence_cannot_support_claim() -> None:
    claim = Claim(id="c1", text="AtlasGrid revenue was USD 999 million.")
    forged = evidence("AtlasGrid revenue was USD 999 million.")
    checked = revalidate_evidence(
        forged,
        "AtlasGrid revenue was USD 120 million.",
    )
    assert checked is None
    judgment = judge_claim(claim, [], [])
    assert judgment.verdict.value not in {"verified", "supported"}
