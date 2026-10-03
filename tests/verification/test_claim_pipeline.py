from datetime import UTC, datetime

from ayorai_attractor.verification.claim_pipeline import (
    ClaimVerificationPipeline,
    RuleScopeClassifier,
)
from ayorai_attractor.verification.extraction import RetrievedDocument, RuleClaimExtractor
from ayorai_attractor.verification.models import Stance
from ayorai_attractor.verification.stance import RuleStanceDetector


def document(doc_id: str, text: str, *, origin: str) -> RetrievedDocument:
    return RetrievedDocument(
        id=doc_id,
        content=text,
        source_id=doc_id,
        source_location=f"fixture://{doc_id}",
        retrieved_at=datetime(2026, 9, 30, tzinfo=UTC),
        origin_id=origin,
        canonical_url=f"https://{doc_id}.example.test",
    )


def pipeline(**kwargs: object) -> ClaimVerificationPipeline:
    return ClaimVerificationPipeline(
        RuleStanceDetector(),
        claim_extractor=RuleClaimExtractor(),
        **kwargs,
    )


def test_pipeline_verifies_caller_supplied_claim_not_document_sentence() -> None:
    claim = "AtlasGrid revenue was USD 120 million."
    result = pipeline().verify(
        [claim],
        [document("e1", "AtlasGrid revenue was USD 130 million.", origin="o1")],
    )
    assert result.claims[0].claim.text == claim
    assert result.claims[0].claim.text != result.evidence[0].excerpt


def test_rule_claim_extractor_only_decomposes_response() -> None:
    response = "AtlasGrid revenue was USD 120 million. AtlasGrid had 800 employees."
    result = RuleClaimExtractor().extract(response)
    assert [item.claim.text for item in result.claims] == [
        "AtlasGrid revenue was USD 120 million.",
        "AtlasGrid had 800 employees.",
    ]


def test_pipeline_reaches_deterministic_judge_for_two_independent_sources() -> None:
    result = pipeline().verify(
        ["AtlasGrid revenue in 2025 was USD 120 million."],
        [
            document("e1", "AtlasGrid revenue in 2025 was USD 120 million.", origin="o1"),
            document(
                "e2",
                "The AtlasGrid annual filing reports USD 120 million of 2025 revenue.",
                origin="o2",
            ),
        ],
    )
    assert result.verdict.value == "verified"
    assert len(result.stances) == 2
    assert all(edge.stance is Stance.SUPPORTS for edge in result.stances)
    assert result.judgments[0].support_clusters == 2


def test_pipeline_detects_conflicting_numeric_evidence() -> None:
    result = pipeline().verify(
        ["AtlasGrid revenue in 2025 was USD 120 million."],
        [
            document("e1", "AtlasGrid revenue in 2025 was USD 120 million.", origin="o1"),
            document("e2", "AtlasGrid revenue in 2025 was USD 130 million.", origin="o2"),
        ],
    )
    assert result.verdict.value == "conflicting"


def test_pipeline_returns_no_answer_abstention_without_retrieval() -> None:
    result = pipeline().verify(
        ["AtlasGrid net income in 2025 is not available."],
        [],
    )
    assert result.status.value == "abstain/no_answer"
    assert result.verdict is None


def test_pipeline_supports_explicit_out_of_scope_boundary() -> None:
    result = pipeline(
        scope_classifier=RuleScopeClassifier(("medical diagnosis",)),
    ).verify(
        ["What medical diagnosis should I give?"],
        [],
    )
    assert result.status.value == "abstain/out_of_scope"
    assert result.verdict is None


def test_pipeline_preserves_provenance_as_part_of_judge_input() -> None:
    result = pipeline().verify(
        ["VectorLabs blocks unsigned model artifacts before deployment."],
        [
            document(
                "e1",
                "VectorLabs blocks unsigned model artifacts before deployment.",
                origin="o1",
            ),
            document(
                "e2",
                "VectorLabs prevents deployment of unsigned model artifacts.",
                origin="o2",
            ),
        ],
    )
    assert result.verdict.value == "verified"
    assert all(item.provenance_complete for item in result.evidence)


def test_pipeline_does_not_upgrade_incomplete_provenance() -> None:
    second = document(
        "e2",
        "VectorLabs blocks unsigned model artifacts before deployment.",
        origin="o2",
    )
    second = RetrievedDocument(**{**second.__dict__, "provenance_complete": False})
    result = pipeline().verify(
        ["VectorLabs blocks unsigned model artifacts before deployment."],
        [
            document(
                "e1",
                "VectorLabs blocks unsigned model artifacts before deployment.",
                origin="o1",
            ),
            second,
        ],
    )
    assert result.verdict.value == "supported"
    assert result.judgments[0].provenance_complete is False


def test_pipeline_contract_rejects_retriever_as_verification_input() -> None:
    import inspect

    signature = inspect.signature(ClaimVerificationPipeline.verify)
    assert list(signature.parameters) == ["self", "claims", "documents"]
    assert "retriever" not in signature.parameters
    result = pipeline().verify(
        ["AtlasGrid revenue was USD 120 million."],
        [
            document(
                "e1",
                "The annual report records USD 120 million in AtlasGrid revenue.",
                origin="o1",
            )
        ],
    )
    assert result.claims[0].claim.text == "AtlasGrid revenue was USD 120 million."
    assert result.claims[0].claim.text != result.evidence[0].excerpt
