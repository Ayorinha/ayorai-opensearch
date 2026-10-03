from datetime import datetime, timezone

from ayorai_attractor.verification.models import Claim, Evidence, Stance, StanceEdge, Verdict
from ayorai_attractor.verification.pipeline import VerificationPipeline


def _evidence(evidence_id: str, claim_id: str) -> Evidence:
    return Evidence(
        id=evidence_id,
        claim_id=claim_id,
        source_id="source-1",
        source_location="page-1",
        retrieved_at=datetime.now(timezone.utc),
        start_offset=0,
        end_offset=10,
        excerpt="The source supports the claim.",
        canonical_url="https://example.com/source",
    )


def test_pipeline_connects_judge_to_grounded_synthesis() -> None:
    claim = Claim(id="c1", text="The claim is supported.")
    evidence = _evidence("e1", claim.id)
    stance = StanceEdge(
        id="s1",
        claim_id=claim.id,
        evidence_id=evidence.id,
        stance=Stance.SUPPORTS,
    )

    result = VerificationPipeline().run([claim], [evidence], [stance])

    assert result.verdict is Verdict.PARTIALLY_SUPPORTED
    assert result.judgments[0].claim_id == "c1"
    assert result.grounding.grounded is True
    assert "[e1]" in result.synthesis.answer


def test_pipeline_abstains_when_no_claim_evidence_exists() -> None:
    claim = Claim(id="c1", text="Unsupported claim.")
    result = VerificationPipeline().run([claim], [], [])

    assert result.verdict is Verdict.UNVERIFIED
    assert result.grounding.grounded is False
    assert result.synthesis.answer.startswith("ABSTAIN:")
