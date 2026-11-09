"""PDF and text ingestion for POST /v1/check (synthetic documents only)."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
from ayorai_attractor.verification.document_ingest import (
    MAX_DOCUMENT_CHARS,
    DocumentIngestError,
    ingest,
)
from tests.pdf_fixture import make_pdf

pytest.importorskip("pypdf")

PAGES = [
    [
        "Título: Duplicata mercantil nº 4521.",
        "O valor do título é de R$ 1.250,00, com vencimento em 10/03/2026.",
    ],
    ["O devedor é a empresa Comercial Alfa Ltda."],
]


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def test_pdf_text_and_page_boundaries() -> None:
    pdf = make_pdf(PAGES)
    doc = ingest(text=None, content_base64=_b64(pdf), media_type="application/pdf")
    assert doc.media_type == "application/pdf"
    assert len(doc.page_starts) == 2
    assert "10/03/2026" in doc.text and "Comercial Alfa" in doc.text
    second = doc.text.index("O devedor")
    assert doc.page_of(second) == 2 and doc.page_of(0) == 1
    assert len(doc.source_sha256) == 64


@pytest.mark.parametrize(
    ("content", "media_type", "message"),
    [
        ("not base64!!", "application/pdf", "base64"),
        (_b64(b"hello"), "application/pdf", "not a PDF"),
        (_b64(make_pdf([[]])), "application/pdf", "no extractable text"),
        (_b64("café".encode("latin-1")), "text/plain", "UTF-8"),
    ],
)
def test_ingest_fails_closed(content: str, media_type: str, message: str) -> None:
    with pytest.raises(DocumentIngestError, match=message):
        ingest(text=None, content_base64=content, media_type=media_type)


def test_ingest_rejects_text_over_character_limit() -> None:
    oversized = "x" * (MAX_DOCUMENT_CHARS + 1)
    with pytest.raises(DocumentIngestError, match="200000 characters"):
        ingest(text=oversized, content_base64=None, media_type=None)
    with pytest.raises(DocumentIngestError, match="200000 characters"):
        ingest(text=None, content_base64=_b64(oversized.encode()), media_type="text/plain")


def test_ingest_rejects_pdf_with_excessive_extracted_text() -> None:
    pdf = make_pdf([["x" * (MAX_DOCUMENT_CHARS + 1)]])
    with pytest.raises(DocumentIngestError, match="200000 characters"):
        ingest(text=None, content_base64=_b64(pdf), media_type="application/pdf")


def test_api_rejects_oversized_base64_text_for_both_document_endpoints() -> None:
    content = _b64(b"x" * (MAX_DOCUMENT_CHARS + 1))
    client = TestClient(app)
    check = client.post(
        "/v1/check",
        json={
            "documents": [{"id": "large", "content_base64": content, "media_type": "text/plain"}],
            "claims": ["Afirmação fictícia."],
        },
    )
    assert check.status_code == 422 and "200000 characters" in check.text
    fields = client.post(
        "/v1/fields",
        json={
            "document": {"id": "large", "content_base64": content, "media_type": "text/plain"},
            "fields": [{"name": "valor", "type": "money", "value": "10,00"}],
        },
    )
    assert fields.status_code == 422 and "200000 characters" in fields.text


def test_api_checks_a_pdf_and_reports_pages() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/check",
        json={
            "documents": [
                {
                    "id": "titulo",
                    "content_base64": _b64(make_pdf(PAGES)),
                    "media_type": "application/pdf",
                    "source": "titulo.pdf",
                }
            ],
            "claims": [
                "O vencimento é em 15/03/2026.",
                "O devedor é a empresa Comercial Alfa Ltda.",
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    digest = body["documents"][0]
    assert digest["media_type"] == "application/pdf" and digest["pages"] == 2
    assert digest["source_sha256"] != digest["sha256"]
    refuted, supported = body["results"]
    assert refuted["status"] == "refuted"
    assert refuted["evidence"][0]["page"] == 1
    assert supported["evidence"][0]["page"] == 2


def test_api_rejects_scanned_pdf_with_clear_message() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/check",
        json={
            "documents": [
                {
                    "id": "scan",
                    "content_base64": _b64(make_pdf([[]])),
                    "media_type": "application/pdf",
                }
            ],
            "claims": ["Qualquer afirmação."],
        },
    )
    assert response.status_code == 422
    assert "OCR" in response.json()["detail"][0]["msg"]


def test_api_requires_media_type_and_single_content() -> None:
    client = TestClient(app)
    base = {"claims": ["x"]}
    no_type = {"documents": [{"id": "a", "content_base64": _b64(b"%PDF-1.4")}], **base}
    both = {
        "documents": [
            {"id": "a", "text": "t", "content_base64": _b64(b"x"), "media_type": "text/plain"}
        ],
        **base,
    }
    assert client.post("/v1/check", json=no_type).status_code == 422
    assert client.post("/v1/check", json=both).status_code == 422
