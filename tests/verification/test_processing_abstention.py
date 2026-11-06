from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ayorai_attractor.models import FailureStage
from ayorai_attractor.verification.claim_pipeline import ClaimVerificationPipeline
from ayorai_attractor.verification.extraction import LLMClaimExtractor, RetrievedDocument
from ayorai_attractor.verification.response import ResponsePolicy
from ayorai_attractor.verification.stance import LLMStanceDetector, RuleStanceDetector


def doc() -> RetrievedDocument:
    text = "AtlasGrid revenue was USD 120 million."
    return RetrievedDocument(
        "e1",
        text,
        "e1",
        "fixture://e1",
        datetime(2026, 9, 30, tzinfo=UTC),
        end_offset=len(text),
        origin_id="o1",
    )


class BadClaimProvider:
    def execute(self, prompt: str):
        return type("R", (), {"text": '{"claims":[{"text":"ok","confidence":2.0}]}'})()


class BadStanceProvider:
    def execute(self, prompt: str):
        return type(
            "R",
            (),
            {"text": '{"evidence_id":"forged","stance":"supports","confidence":1.0}'},
        )()


def test_llm_claim_schema_is_strict() -> None:
    try:
        LLMClaimExtractor(BadClaimProvider(), model="fixture", version="1").extract("response")
    except ValidationError:
        pass
    else:
        raise AssertionError("invalid confidence must be rejected")


def test_invalid_llm_evidence_id_abstains_with_reason() -> None:
    pipeline = ClaimVerificationPipeline(
        LLMStanceDetector(BadStanceProvider(), model="fixture", version="1")
    )
    result = pipeline.verify(["AtlasGrid revenue was USD 120 million."], [doc()])
    assert result.status is ResponsePolicy.ABSTAIN_PROCESSING_ERROR
    assert result.abstention_reason == "ValueError"
    assert result.failure_stage is FailureStage.NLI
    assert "unknown evidence id" in result.rationale


def test_claim_extraction_failure_reports_extraction_stage() -> None:
    pipeline = ClaimVerificationPipeline(
        LLMStanceDetector(BadStanceProvider(), model="fixture", version="1"),
        claim_extractor=LLMClaimExtractor(BadClaimProvider(), model="fixture", version="1"),
    )

    result = pipeline.verify_response("AtlasGrid revenue was USD 120 million.", [doc()])

    assert result.status is ResponsePolicy.ABSTAIN_PROCESSING_ERROR
    assert result.failure_stage is FailureStage.EXTRACTION
    assert result.abstention_reason == "ValidationError"


def test_judge_failure_reports_judge_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_judge(*args: object, **kwargs: object) -> None:
        raise ValueError("synthetic judge failure")

    monkeypatch.setattr("ayorai_attractor.verification.claim_pipeline.judge", fail_judge)
    pipeline = ClaimVerificationPipeline(RuleStanceDetector())

    result = pipeline.verify(["AtlasGrid revenue was USD 120 million."], [doc()])

    assert result.status is ResponsePolicy.ABSTAIN_PROCESSING_ERROR
    assert result.failure_stage is FailureStage.JUDGE
    assert len(result.stances) == 1
