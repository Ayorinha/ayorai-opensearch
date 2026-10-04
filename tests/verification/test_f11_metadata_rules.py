from datetime import UTC, datetime

from ayorai_attractor.verification.clusters import cluster_evidence, dependency_reason
from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.judge import judge_claim
from ayorai_attractor.verification.models import (
    Claim,
    Evidence,
    Stance,
    StanceEdge,
    Verdict,
)
from ayorai_attractor.verification.stance import (
    RuleStanceDetector,
    _numeric_facts,
    _numeric_facts_align,
)


def evidence(
    evidence_id: str,
    *,
    source_id: str,
    origin_id: str | None = None,
    normalized_hash: str | None = None,
    cited_origin_id: str | None = None,
    excerpt: str = "Revenue was 100.",
) -> Evidence:
    return Evidence(
        id=evidence_id,
        claim_id="c1",
        source_id=source_id,
        source_location="body",
        retrieved_at=datetime(2026, 10, 3, tzinfo=UTC),
        start_offset=0,
        end_offset=len(excerpt),
        excerpt=excerpt,
        origin_id=f"origin-{evidence_id}" if origin_id is None else origin_id,
        canonical_url=None,
        normalized_content_hash=normalized_hash,
        cited_origin_id=cited_origin_id,
    )


def claim_item(text: str) -> ExtractedClaim:
    return ExtractedClaim(
        claim=Claim(id="c1", text=text),
        confidence=1.0,
        provenance=ComponentProvenance("test", "fake", "1", "in", "out"),
    )


def test_same_source_id_is_not_independent() -> None:
    left = evidence("e1", source_id="source-a")
    right = evidence("e2", source_id="source-a")
    assert dependency_reason(left, right) == "same_source_id"
    assert cluster_evidence([left, right]) == [frozenset({"e1", "e2"})]


def test_same_hash_is_not_independent_even_with_distinct_sources() -> None:
    left = evidence("e1", source_id="source-a", normalized_hash="h")
    right = evidence("e2", source_id="source-b", normalized_hash="h")
    assert dependency_reason(left, right) == "same_normalized_content_hash"


def test_citation_republication_is_transitive() -> None:
    original = evidence("e1", source_id="a", origin_id="origin-a")
    republication = evidence("e2", source_id="b", origin_id="origin-b", cited_origin_id="origin-a")
    third = evidence("e3", source_id="c", cited_origin_id="origin-b")
    clusters = cluster_evidence([original, republication, third])
    assert clusters == [frozenset({"e1", "e2", "e3"})]


def test_missing_dependency_metadata_is_unknown_and_not_a_cluster() -> None:
    left = evidence("e1", source_id="source-a")
    right = evidence("e2", source_id="source-b")
    left = left.model_copy(update={"origin_id": None})
    right = right.model_copy(update={"origin_id": None})
    assert dependency_reason(left, right) is None
    assert len(cluster_evidence([left, right])) == 2


def test_numeric_absolute_agreement_below_relative_tolerance_supports() -> None:
    claim = claim_item("Revenue was 100 million USD.")
    item = evidence("e1", source_id="source-a", excerpt="Revenue was 100.5 million USD.")
    result = RuleStanceDetector().detect([claim], [item])
    assert result.edges[0].edge.stance is Stance.SUPPORTS


def test_numeric_boundary_is_inclusive() -> None:
    claim = claim_item("Revenue was 100 million USD.")
    item = evidence("e1", source_id="source-a", excerpt="Revenue was 101 million USD.")
    result = RuleStanceDetector().detect([claim], [item])
    assert result.edges[0].edge.stance is Stance.SUPPORTS


def test_numeric_value_beyond_tolerance_contradicts_even_with_low_lexical_overlap() -> None:
    claim = claim_item("Revenue was 100 million USD.")
    item = evidence("e1", source_id="source-a", excerpt="Revenue was 120 million USD.")
    result = RuleStanceDetector().detect([claim], [item])
    assert result.edges[0].edge.stance is Stance.CONTRADICTS


def test_incomplete_retrieval_metadata_is_preserved() -> None:
    from ayorai_attractor.evaluation.golden import FixtureRetriever

    docs = {
        "doc-a": {
            "doc_id": "doc-a",
            "content": "VectorLabs blocks unsigned model artifacts before deployment.",
            "url": "https://example.test/a",
            "origin_id": "origin-a",
            "offsets": [0, 57],
        }
    }
    evidence = FixtureRetriever(docs, ["doc-a"]).retrieve("query")[0].to_evidence(
        "c1",
        evidence_id="e1",
    )
    assert evidence.provenance_complete is False


def test_numeric_mismatch_with_different_attribute_is_neutral() -> None:
    claim = claim_item("Revenue was 100 million USD.")
    item = evidence("e1", source_id="source-a", excerpt="Profit was 120 million USD.")
    result = RuleStanceDetector().detect([claim], [item])
    assert result.edges[0].edge.stance is Stance.NEUTRAL


def test_same_number_with_different_entity_is_neutral() -> None:
    claim = claim_item("Company X revenue was 100 million USD.")
    item = evidence(
        "e1", source_id="source-a", excerpt="Company Y revenue was 100 million USD."
    )
    result = RuleStanceDetector().detect([claim], [item])
    assert result.edges[0].edge.stance is Stance.NEUTRAL


def test_pt_en_numeric_conflict_is_contradiction() -> None:
    claim = claim_item("A receita da Empresa X foi de 100 milhões de USD.")
    item = evidence("e1", source_id="source-a", excerpt="Company X revenue was 120 million USD.")
    result = RuleStanceDetector().detect([claim], [item])
    assert result.edges[0].edge.stance is Stance.CONTRADICTS


def test_unknown_provenance_does_not_count_for_verified() -> None:
    item = evidence("e1", source_id="source-a").model_copy(update={"provenance_complete": False})
    claim = Claim(id="c1", text="Revenue was 100 million USD.")
    edge = StanceEdge(
        id="s1",
        claim_id="c1",
        evidence_id="e1",
        stance=Stance.SUPPORTS,
    )
    judgment = judge_claim(claim, [item], [edge])
    assert judgment.support_clusters == 1
    assert judgment.verdict is Verdict.PARTIALLY_SUPPORTED


def test_numeric_alignment_internal_contracts() -> None:
    assert _numeric_facts("Revenue was 100 million USD.") == [
        ("100", "usd:million", "revenue")
    ]
    assert _numeric_facts("The figure is 120 million USD.") == [
        ("120", "usd:million", "figure")
    ]
    assert _numeric_facts_align(
        "Revenue was 100 million USD.", "The figure is 120 million USD."
    ) == (False, False, False)
    assert _numeric_facts_align(
        "Revenue was 100 million USD.", "Revenue was 120 million USD."
    ) == (True, False, True)
