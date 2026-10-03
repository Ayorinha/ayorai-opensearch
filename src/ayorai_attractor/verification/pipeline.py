"""End-to-end deterministic verification and synthesis pipeline."""

from dataclasses import dataclass

from ayorai_attractor.synthesis import GroundedSynthesizer, GroundingResult, SynthesisResult

from .judge import ClaimJudgment, judge
from .models import Claim, Evidence, StanceEdge, Verdict


@dataclass(frozen=True)
class VerificationPipelineResult:
    judgments: tuple[ClaimJudgment, ...]
    verdict: Verdict
    synthesis: SynthesisResult
    grounding: GroundingResult


class VerificationPipeline:
    """Connect structured verification to the R6 grounded-answer gate."""

    def __init__(self, synthesizer: GroundedSynthesizer | None = None) -> None:
        self.synthesizer = synthesizer or GroundedSynthesizer()

    def run(
        self,
        claims: list[Claim],
        evidence: list[Evidence],
        stances: list[StanceEdge],
    ) -> VerificationPipelineResult:
        judgments, verdict = judge(claims, evidence, stances)
        evidence_by_claim = {
            claim.id: [item.id for item in evidence if item.claim_id == claim.id]
            for claim in claims
        }
        citations = {
            claim.text: evidence_by_claim[claim.id]
            for claim in claims
        }
        available = {item.id for item in evidence}
        synthesis = self.synthesizer.synthesize(
            [claim.text for claim in claims],
            citations,
            available,
        )
        return VerificationPipelineResult(
            judgments=tuple(judgments),
            verdict=verdict,
            synthesis=synthesis,
            grounding=synthesis.grounding,
        )
