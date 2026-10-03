from datetime import datetime, timezone

from ayorai_attractor.verification.claim_pipeline import (
    ClaimVerificationPipeline,
    RuleScopeClassifier,
)
from ayorai_attractor.verification.extraction import RetrievedDocument, RuleClaimExtractor
from ayorai_attractor.verification.models import Stance
from ayorai_attractor.verification.stance import RuleStanceDetector


class FixtureRetriever:
    def __init__(self, documents: list[RetrievedDocument]) -> None:
        self.documents = documents

    def retrieve(self, query: str) -> list[RetrievedDocument]:
        del query
        return self.documents


def document(
    doc_id: str,
    text: str,
    *,
    origin: str,
    retrieved: bool = True,
) -> RetrievedDocument:
    return RetrievedDocument(
        id=doc_id,
        content=text,
        source_id=doc_id,
        source_location=f"fixture://{doc_id}",
        retrieved_at=(
            datetime(2026, 9, 30, tzinfo=timezone.utc)
            if retrieved
            else datetime(2026, 9, 30, tzinfo=timezone.utc)
        ),
        origin_id=origin,
        canonical_url=f"https://{doc_id}.example.test",
    )


def pipeline(documents: list[RetrievedDocument], **kwargs: object) -> ClaimVerificationPipeline:
    return ClaimVerificationPipeline(
        FixtureRetriever(documents),
        RuleClaimExtractor(),
        RuleStanceDetector(),
        **kwargs,
    )


def test_pipeline_reaches_deterministic_judge_for_two_independent_sources() -> None:
    result = pipeline(
        [
            document("e1", "AtlasGrid revenue in 2025 was USD 120 million.", origin="o1"),
            document("e2", "AtlasGrid revenue in 2025 was USD 120 million.", origin="o2"),
        ]
    ).verify("What was AtlasGrid revenue in 2025?")

    assert result.verdict.value == "verified"
    assert result.status.value == "verified"
    assert len(result.claims) == 1
    assert len(result.stances) == 2
    assert all(edge.stance is Stance.SUPPORTS for edge in result.stances)
    assert result.judgments[0].support_clusters == 2


def test_pipeline_detects_conflicting_numeric_evidence() -> None:
    result = pipeline(
        [
            document("e1", "AtlasGrid revenue in 2025 was USD 120 million.", origin="o1"),
            document("e2", "AtlasGrid revenue in 2025 was USD 130 million.", origin="o2"),
        ]
    ).verify("Compare AtlasGrid revenue in 2025.")

    assert result.verdict.value == "conflicting"
    assert result.judgments[0].contradiction_clusters == 1


def test_pipeline_returns_no_answer_abstention_without_retrieval() -> None:
    result = pipeline([]).verify("What was AtlasGrid net income in 2025?")

    assert result.status.value == "abstain/no_answer"
    assert result.verdict is None


def test_pipeline_supports_explicit_out_of_scope_boundary() -> None:
    result = pipeline(
        [],
        scope_classifier=RuleScopeClassifier(("medical diagnosis",)),
    ).verify("What medical diagnosis should I give?")

    assert result.status.value == "abstain/out_of_scope"
    assert result.verdict is None


def test_pipeline_preserves_provenance_as_part_of_judge_input() -> None:
    result = pipeline(
        [
            document(\n                "e1",\n                "VectorLabs blocks unsigned model artifacts before deployment.",\n                origin="o1",\n            ),
            document(\n                "e2",\n                "VectorLabs blocks unsigned model artifacts before deployment.",\n                origin="o2",\n            ),
        ]
    ).verify("Does VectorLabs block unsigned model artifacts before deployment?")

    assert result.verdict.value == "verified"
    assert all(item.provenance_complete for item in result.evidence)


def test_pipeline_does_not_upgrade_incomplete_provenance() -> None:
    first = document(
        "e1",
        "VectorLabs blocks unsigned model artifacts before deployment.",
        origin="o1",
    )
    second = document(
        "e2",
        "VectorLabs blocks unsigned model artifacts before deployment.",
        origin="o2",
    )
    second = RetrievedDocument(
        **{**second.__dict__, "provenance_complete": False},
    )
    result = pipeline([first, second]).verify(
        "Does VectorLabs block unsigned model artifacts before deployment?"
    )

    assert result.verdict.value == "supported"
    assert result.judgments[0].provenance_complete is False
