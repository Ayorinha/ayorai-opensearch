from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.models import Claim, Evidence
from ayorai_attractor.verification.stance import TranslatedNLIStanceDetector


class _Backend:
    def classify(self, claim: str, evidence: str) -> dict[str, object]:
        assert claim == "Revenue increased."
        assert evidence == "Revenue increased."
        return {"stance": "supports", "confidence": 0.9}


class _Translator:
    provenance_version = "fixture-translator-v1"

    def translate(self, text: str) -> str:
        assert text == "A receita aumentou."
        return "Revenue increased."

    def provenance_hash(self, source: str, translated: str) -> str:
        return hashlib.sha256(f"{source}\n{translated}".encode()).hexdigest()


def test_translated_document_provenance_uses_original_offsets_and_text() -> None:
    claim = ExtractedClaim(
        claim=Claim(id="clm_001", text="Revenue increased."),
        confidence=1.0,
        provenance=ComponentProvenance(
            "test",
            "fixture",
            "1",
            "input",
            "output",
        ),
    )
    document = "A receita aumentou."
    evidence = Evidence(
        id="ev_001",
        claim_id="clm_001",
        source_id="src_001",
        source_location="fixture",
        retrieved_at=datetime(2026, 10, 3, tzinfo=UTC),
        start_offset=37,
        end_offset=37 + len(document),
        excerpt=document,
        origin_id="origin_001",
    )

    result = TranslatedNLIStanceDetector(
        _Backend(),
        _Translator(),
        model="fixture-model",
        version="fixture-version",
    ).detect([claim], [evidence])

    provenance = result.edges[0].provenance
    assert provenance.version == (
        "fixture-version|window=37:56|"
        "translation="
        + hashlib.sha256(
            f"{document}\nRevenue increased.".encode()
        ).hexdigest()
    )
    assert provenance.input_sha256 == hashlib.sha256(
        f"Revenue increased.\n{document}".encode()
    ).hexdigest()
