from datetime import UTC, datetime
import hashlib
import json

import pytest
from pydantic import ValidationError

from ayorai_attractor.providers.base import ProviderResponse
from ayorai_attractor.verification.extraction import (
    LLMClaimExtractor,
    NLIClaimExtractor,
    RetrievedDocument,
    RuleClaimExtractor,
)


class StubNLIBackend:
    def __init__(self, claims: list[dict[str, object]]) -> None:
        self.claims = claims
        self.received: str | None = None

    def extract_claims(self, response: str) -> list[dict[str, object]]:
        self.received = response
        return self.claims


class StubProvider:
    def __init__(self, text: str) -> None:
        self.text = text
        self.prompt: str | None = None

    def execute(self, prompt: str) -> ProviderResponse:
        self.prompt = prompt
        return ProviderResponse(text=self.text, source="test-provider")


def test_rule_extractor_empty_response_has_no_claims() -> None:
    assert RuleClaimExtractor().extract("  \n  ").claims == ()


def test_rule_extractor_records_deterministic_hashes_and_ids() -> None:
    extractor = RuleClaimExtractor()
    response = "A receita foi de R$ 10 milhões. A equipe tinha 20 pessoas."

    first = extractor.extract(response)
    second = extractor.extract(response)

    assert [item.claim.id for item in first.claims] == ["clm_001", "clm_002"]
    assert first == second
    assert all(
        item.provenance.input_sha256 == hashlib.sha256(response.encode("utf-8")).hexdigest()
        for item in first.claims
    )
    assert all(item.provenance.component == "claim_extractor.rule" for item in first.claims)


def test_nli_extractor_records_backend_input_and_default_confidence() -> None:
    backend = StubNLIBackend([{"text": "A afirmação factual."}])
    result = NLIClaimExtractor(backend, model="local-nli", version="1.2").extract("Resposta original.")

    assert backend.received == "Resposta original."
    assert result.claims[0].claim.id == "clm_001"
    assert result.claims[0].claim.text == "A afirmação factual."
    assert result.claims[0].confidence == 0.0
    assert result.claims[0].provenance.model == "local-nli"
    assert result.claims[0].provenance.version == "1.2"


def test_llm_extractor_builds_prompt_and_validates_response() -> None:
    provider = StubProvider(
        json.dumps({"claims": [{"text": "A taxa foi de 5%.", "confidence": 0.8}]})
    )
    result = LLMClaimExtractor(provider, model="fixture-llm", version="test").extract(
        "A resposta original."
    )

    assert provider.prompt is not None
    prompt = json.loads(provider.prompt)
    assert prompt["response"] == "A resposta original."
    assert prompt["task"] == "decompose the model response into atomic factual claims"
    assert result.claims[0].claim.text == "A taxa foi de 5%."
    assert result.claims[0].confidence == 0.8
    assert result.claims[0].provenance.input_sha256 == hashlib.sha256(
        "A resposta original.".encode("utf-8")
    ).hexdigest()


@pytest.mark.parametrize(
    "payload",
    [
        '{"claims": []}',
        '{"claims": [{"text": "x", "confidence": 1.2}]}',
        '{"claims": [{"text": "x", "confidence": 0.5, "extra": true}]}',
        '{"claims": [{"text": "", "confidence": 0.5}]}',
    ],
)
def test_llm_extractor_rejects_invalid_claim_payloads(payload: str) -> None:
    extractor = LLMClaimExtractor(
        StubProvider(payload),
        model="fixture-llm",
        version="test",
    )

    with pytest.raises(ValidationError):
        extractor.extract("A resposta original.")


def test_retrieved_document_builds_evidence_with_content_hash_and_offsets() -> None:
    content = "Trecho documental."
    document = RetrievedDocument(
        id="doc-1",
        content=content,
        source_id="source-1",
        source_location="fixture://doc-1",
        retrieved_at=datetime(2026, 10, 21, tzinfo=UTC),
        origin_id="origin-1",
        start_offset=4,
        end_offset=10,
    )

    evidence = document.to_evidence("claim-1", evidence_id="evidence-1")

    assert evidence.id == "evidence-1"
    assert evidence.claim_id == "claim-1"
    assert evidence.start_offset == 4
    assert evidence.end_offset == 10
    assert evidence.normalized_content_hash == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert evidence.provenance_complete is True


def test_retrieved_document_uses_content_length_when_end_offset_is_missing() -> None:
    content = "Fonte documental."
    document = RetrievedDocument(
        id="doc-2",
        content=content,
        source_id="source-2",
        source_location="fixture://doc-2",
        retrieved_at=datetime(2026, 10, 21, tzinfo=UTC),
        canonical_url="https://example.test/source",
    )

    evidence = document.to_evidence("claim-2")

    assert evidence.id == "doc-2"
    assert evidence.end_offset == len(content)
    assert str(evidence.canonical_url) == "https://example.test/source"
    assert evidence.origin_id is None
