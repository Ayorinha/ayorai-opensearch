from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ayorai_attractor.verification.claim_pipeline import ClaimVerificationPipeline
from ayorai_attractor.verification.extraction import RetrievedDocument, RuleClaimExtractor
from ayorai_attractor.verification.stance import RuleStanceDetector

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "paraphrase-invariance-v1.json"
RETRIEVED_AT = datetime(2026, 10, 31, tzinfo=UTC)


def _document(record: dict[str, Any]) -> RetrievedDocument:
    return RetrievedDocument(
        id=record["id"],
        content=record["text"],
        source_id=record["id"],
        source_location=f"fixture://{record['id']}",
        retrieved_at=RETRIEVED_AT,
        origin_id=record["origin"],
    )


def _pipeline() -> ClaimVerificationPipeline:
    return ClaimVerificationPipeline(
        RuleStanceDetector(),
        claim_extractor=RuleClaimExtractor(),
    )


def test_synthetic_paraphrases_preserve_the_expected_verdict() -> None:
    """Equivalent synthetic claims must retain one expected deterministic verdict."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["dataset_id"] == "paraphrase-invariance-synthetic-v1"
    assert len(payload["groups"]) >= 2
    verdicts = {group["expected_verdict"] for group in payload["groups"]}
    assert {"verified", "refuted"} <= verdicts, "fixture must cover supported and refuted claims"

    verifier = _pipeline()
    for group in payload["groups"]:
        claims = group["claims"]
        documents = [_document(item) for item in group["documents"]]
        expected = group["expected_verdict"]
        assert len(claims) >= 2
        assert len({item.origin_id for item in documents}) >= 2

        observed = []
        for claim in claims:
            result = verifier.verify([claim], documents)
            assert result.verdict is not None, (
                f"{group['group_id']}: no verdict for paraphrase {claim!r}"
            )
            observed.append(result.verdict.value)

        assert observed == [expected] * len(claims), (
            f"{group['group_id']}: expected {expected!r} for every paraphrase; "
            f"observed {observed!r}"
        )
