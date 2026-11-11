"""Field-by-field comparison (synthetic, fictitious protest data only)."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
from ayorai_attractor.verification.document_ingest import IngestedDocument, ingest
from ayorai_attractor.verification.field_check import (
    FieldSpec,
    check_field,
    cpf_cnpj_is_valid,
    normalize_date,
    normalize_money,
)
from tests.pdf_fixture import make_pdf

DOC = """DUPLICATA MERCANTIL Nº 4521
Sacador: Distribuidora Beta S.A. - CNPJ 11.222.333/0001-81
Sacado (devedor): Comercial Alfa Ltda. - CNPJ 45.723.174/0001-10
Emissão: 10/01/2026
Valor: R$ 1.250,00
Vencimento: 10/03/2026
Endosso translativo ao Banco Beta S.A."""


def _outcome(spec: FieldSpec) -> str:
    return check_field(DOC, spec).outcome


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("R$ 1.250,00", "1250.00"),
        ("1250,00", "1250.00"),
        ("1,250.00", "1250.00"),
        ("1250", "1250.00"),
        ("12,5", None),
    ],
)
def test_money_normalisation(raw: str, expected: str | None) -> None:
    assert normalize_money(raw) == expected


def test_date_normalisation() -> None:
    assert normalize_date("10/03/2026") == "2026-03-10"
    assert normalize_date("2026-03-10") == "2026-03-10"
    assert normalize_date("31/02/2026") is None


def test_cpf_cnpj_check_digits() -> None:
    assert cpf_cnpj_is_valid("11222333000181")
    assert not cpf_cnpj_is_valid("11222333000100")
    assert cpf_cnpj_is_valid("52998224725")
    assert not cpf_cnpj_is_valid("11111111111")


def test_equal_values_are_conforme_in_any_format() -> None:
    assert _outcome(FieldSpec("valor", "money", "1250.00", ("valor",))) == "conforme"
    assert _outcome(FieldSpec("venc", "date", "2026-03-10", ("vencimento",))) == "conforme"
    cnpj = FieldSpec("cnpj", "cpf_cnpj", "45723174000110", ("sacado", "devedor"))
    assert _outcome(cnpj) == "conforme"
    assert _outcome(FieldSpec("nome", "text", "COMERCIAL ALFA LTDA", ("sacado",))) == "conforme"


def test_wrong_date_is_divergente_with_document_value() -> None:
    result = check_field(DOC, FieldSpec("venc", "date", "15/03/2026", ("vencimento",)))
    assert result.outcome == "divergente"
    assert result.found == "10/03/2026" and result.found_normalized == "2026-03-10"
    assert result.start is not None and DOC[result.start : result.end] == "10/03/2026"
    assert result.excerpt == "Vencimento: 10/03/2026"


def test_label_disambiguates_dates_and_cnpjs() -> None:
    # The emission date is not mistaken for the due date, and vice versa.
    assert _outcome(FieldSpec("venc", "date", "10/01/2026", ("vencimento",))) == "divergente"
    assert _outcome(FieldSpec("emissao", "date", "10/01/2026", ("emissão",))) == "conforme"
    # The drawer's CNPJ on another line is not the debtor's.
    debtor = FieldSpec("cnpj", "cpf_cnpj", "11.222.333/0001-81", ("sacado",))
    result = check_field(DOC, debtor)
    assert result.outcome == "divergente" and result.found == "45.723.174/0001-10"


def test_wrong_amount_is_divergente() -> None:
    result = check_field(DOC, FieldSpec("valor", "money", "R$ 1.520,00", ("valor",)))
    assert result.outcome == "divergente" and result.found_normalized == "1250.00"


def test_other_entity_is_divergente_and_absent_label_abstains() -> None:
    result = check_field(DOC, FieldSpec("endosso", "text", "Banco Gama S.A.", ("endosso",)))
    assert result.outcome == "divergente" and result.found == "translativo ao Banco Beta S.A"
    assert _outcome(FieldSpec("aval", "text", "Banco Gama S.A.", ("avalista",))) == "ausente"
    assert _outcome(FieldSpec("protocolo", "number", "77", ("protocolo",))) == "ausente"


def test_malformed_expected_value_is_invalido() -> None:
    assert _outcome(FieldSpec("cnpj", "cpf_cnpj", "11.222.333/0001-00", ("sacador",))) == "invalido"
    assert _outcome(FieldSpec("valor", "money", "mil reais", ("valor",))) == "invalido"


def test_unlabelled_field_searches_whole_document() -> None:
    assert _outcome(FieldSpec("valor", "money", "1250,00")) == "conforme"
    assert _outcome(FieldSpec("valor", "money", "999,00")) == "ausente"


def test_unknown_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        check_field(DOC, FieldSpec("x", "iban", "1"))


# ---------------------------------------------------------------- API


def _fields() -> list[dict]:
    return [
        {"name": "valor", "type": "money", "value": "1250.00", "labels": ["valor"]},
        {"name": "vencimento", "type": "date", "value": "15/03/2026", "labels": ["vencimento"]},
        {"name": "endosso", "type": "text", "value": "Banco Gama S.A.", "labels": ["endosso"]},
        {"name": "sacador", "type": "cpf_cnpj", "value": "11.222.333/0001-00"},
    ]


def test_api_fields_text_document() -> None:
    client = TestClient(app)
    body = {"document": {"id": "titulo-1", "text": DOC}, "fields": _fields()}
    response = client.post("/v1/fields", json=body)
    assert response.status_code == 200, response.text
    payload = response.json()
    outcomes = {item["name"]: item["outcome"] for item in payload["results"]}
    assert outcomes == {
        "valor": "conforme",
        "vencimento": "divergente",
        "endosso": "divergente",
        "sacador": "invalido",
    }
    assert payload["summary"] == {
        "conforme": 1,
        "divergente": 2,
        "ambiguo": 0,
        "ausente": 0,
        "invalido": 1,
    }
    assert payload["trace_id"].startswith("fld_")
    assert client.post("/v1/fields", json=body).json()["trace_id"] == payload["trace_id"]


def test_api_fields_pdf_reports_page() -> None:
    pytest.importorskip("pypdf")
    pdf = make_pdf([["Duplicata nº 4521."], ["Valor: R$ 1.250,00", "Vencimento: 10/03/2026"]])
    body = {
        "document": {
            "id": "titulo-pdf",
            "content_base64": base64.b64encode(pdf).decode(),
            "media_type": "application/pdf",
        },
        "fields": [
            {"name": "vencimento", "type": "date", "value": "10/03/2026", "labels": ["vencimento"]}
        ],
    }
    response = TestClient(app).post("/v1/fields", json=body)
    assert response.status_code == 200, response.text
    result = response.json()["results"][0]
    assert result["outcome"] == "conforme" and result["page"] == 2


def test_api_fields_trace_id_binds_source_and_page_layout() -> None:
    pytest.importorskip("pypdf")
    client = TestClient(app)
    pdf = make_pdf([["Identificação"], ["Valor: R$ 10,00"]])
    encoded = base64.b64encode(pdf).decode()
    ingested = ingest(text=None, content_base64=encoded, media_type="application/pdf")
    fields = [{"name": "valor", "type": "money", "value": "10,00", "labels": ["Valor"]}]

    pdf_response = client.post(
        "/v1/fields",
        json={
            "document": {
                "id": "same-document",
                "content_base64": encoded,
                "media_type": "application/pdf",
            },
            "fields": fields,
        },
    )
    text_response = client.post(
        "/v1/fields",
        json={"document": {"id": "same-document", "text": ingested.text}, "fields": fields},
    )

    assert pdf_response.status_code == 200, pdf_response.text
    assert text_response.status_code == 200, text_response.text
    pdf_body = pdf_response.json()
    text_body = text_response.json()
    assert pdf_body["document"]["sha256"] == text_body["document"]["sha256"]
    assert pdf_body["results"][0]["page"] == 2
    assert text_body["results"][0]["page"] == 1
    assert pdf_body["trace_id"] != text_body["trace_id"]
    assert pdf_body["engine"]["trace"] == "fields-trace-2"


def test_api_fields_trace_id_isolates_page_boundary_identity(monkeypatch) -> None:
    import ayorai_attractor.api.app as api_module

    layouts = iter(((0,), (0, 1)))
    text = "Valor: R$ 10,00"
    source_sha256 = "c" * 64

    def fake_ingest(*, text, content_base64, media_type):
        return IngestedDocument(
            text="Valor: R$ 10,00",
            media_type="application/pdf",
            page_starts=next(layouts),
            source_sha256=source_sha256,
        )

    monkeypatch.setattr(api_module, "ingest", fake_ingest)
    client = TestClient(app)
    body = {
        "document": {"id": "same-document", "text": text},
        "fields": [
            {"name": "valor", "type": "money", "value": "10,00", "labels": ["Valor"]}
        ],
    }

    first = client.post("/v1/fields", json=body)
    second = client.post("/v1/fields", json=body)

    assert first.status_code == second.status_code == 200
    first_body, second_body = first.json(), second.json()
    assert first_body["document"]["sha256"] == second_body["document"]["sha256"]
    assert first_body["document"]["source_sha256"] == second_body["document"]["source_sha256"]
    assert first_body["document"]["media_type"] == second_body["document"]["media_type"]
    assert first_body["trace_id"] != second_body["trace_id"]
    assert first_body["results"][0]["page"] == 1
    assert second_body["results"][0]["page"] == 2


def test_api_fields_trace_id_binds_document_id() -> None:
    client = TestClient(app)
    fields = _fields()
    first = client.post(
        "/v1/fields", json={"document": {"id": "document-a", "text": DOC}, "fields": fields}
    )
    second = client.post(
        "/v1/fields", json={"document": {"id": "document-b", "text": DOC}, "fields": fields}
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["trace_id"] != second.json()["trace_id"]


def test_api_fields_trace_id_binds_submitted_field_specification() -> None:
    client = TestClient(app)
    document = {"id": "same-document", "text": "Valor: R$ 10,00"}
    base_fields = [{"name": "valor", "type": "money", "value": "10,00", "labels": ["Valor"]}]

    baseline = client.post("/v1/fields", json={"document": document, "fields": base_fields})
    changed_value = client.post(
        "/v1/fields",
        json={
            "document": document,
            "fields": [{"name": "valor", "type": "money", "value": "11,00", "labels": ["Valor"]}],
        },
    )
    changed_label = client.post(
        "/v1/fields",
        json={
            "document": document,
            "fields": [
                {"name": "valor", "type": "money", "value": "10,00", "labels": ["Montante"]}
            ],
        },
    )

    assert baseline.status_code == changed_value.status_code == changed_label.status_code == 200
    baseline_trace = baseline.json()["trace_id"]
    assert changed_value.json()["trace_id"] != baseline_trace
    assert changed_label.json()["trace_id"] != baseline_trace


def test_api_fields_rejects_duplicate_names() -> None:
    fields = _fields()[:1] * 2
    response = TestClient(app).post(
        "/v1/fields", json={"document": {"id": "d", "text": DOC}, "fields": fields}
    )
    assert response.status_code == 422


def test_api_check_long_url_is_not_a_server_error() -> None:
    # Regression: a URL at the 2083-character limit gained a trailing slash when
    # normalised and crashed evidence validation (HTTP 500). Found by Schemathesis.
    url = "https://" + ".".join(["a" * 63] * 32)[:2075]
    body = {"answer": "0", "documents": [{"id": "0", "text": "0", "url": url}]}
    response = TestClient(app).post("/v1/check", json=body)
    assert response.status_code == 422
    short = {"answer": "0", "documents": [{"id": "0", "text": "0", "url": "https://a.example"}]}
    assert TestClient(app).post("/v1/check", json=short).status_code == 200


def test_api_fields_rejects_blank_expected_values_and_labels() -> None:
    client = TestClient(app)
    document = {"id": "synthetic", "text": "Valor: R$ 10,00"}
    for value in ("", " ", "   ", "\n\t ", "\r\n"):
        response = client.post(
            "/v1/fields",
            json={
                "document": document,
                "fields": [{"name": "valor", "type": "money", "value": value}],
            },
        )
        assert response.status_code == 422, response.text

    for label in ("", " ", "   ", "\n\t ", "\r\n"):
        response = client.post(
            "/v1/fields",
            json={
                "document": document,
                "fields": [{"name": "valor", "type": "money", "value": "10", "labels": [label]}],
            },
        )
        assert response.status_code == 422, response.text
