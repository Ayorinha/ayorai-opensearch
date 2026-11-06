from __future__ import annotations

import socket
from datetime import UTC, datetime

import pytest

from ayorai_attractor.verification.claim_pipeline import ClaimVerificationPipeline
from ayorai_attractor.verification.extraction import RetrievedDocument
from ayorai_attractor.verification.stance import RuleStanceDetector

RETRIEVED_AT = datetime(2026, 10, 31, tzinfo=UTC)


def _document(document_id: str, origin_id: str, text: str) -> RetrievedDocument:
    return RetrievedDocument(
        id=document_id,
        content=text,
        source_id=document_id,
        source_location=f"fixture://{document_id}",
        retrieved_at=RETRIEVED_AT,
        origin_id=origin_id,
    )


def _deny_network(*args: object, **kwargs: object) -> None:
    raise AssertionError("offline verification attempted a socket network operation")


def test_local_verification_succeeds_with_socket_network_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The deterministic local pipeline must not need DNS or a network socket."""
    for operation in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, operation, _deny_network)
    monkeypatch.setattr(socket, "create_connection", _deny_network)
    monkeypatch.setattr(socket, "getaddrinfo", _deny_network)

    verifier = ClaimVerificationPipeline(RuleStanceDetector())
    result = verifier.verify(
        ["AtlasGrid revenue in 2025 was USD 120 million."],
        [
            _document(
                "atlasgrid-source-a",
                "atlasgrid-origin-a",
                "AtlasGrid revenue in 2025 was USD 120 million.",
            ),
            _document(
                "atlasgrid-source-b",
                "atlasgrid-origin-b",
                "The AtlasGrid annual filing reports USD 120 million of 2025 revenue.",
            ),
        ],
    )

    assert result.verdict is not None
    assert result.verdict.value == "verified"
    assert len(result.evidence) == 2
    assert len(result.stances) == 2
