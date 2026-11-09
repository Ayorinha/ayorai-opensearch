"""POST /v1/check — claims or an answer checked against supplied documents."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ayorai_attractor.api.app import app
from ayorai_attractor.verification.document_check import (
    CheckDocumentInput,
    ConservativeStanceDetector,
    check_documents,
    split_passages,
)

TITLE = (
    "Título: Duplicata mercantil nº 4521.\n\n"
    "O valor do título é de R$ 1.250,00, com vencimento em 10/03/2026.\n"
    "O devedor é a empresa Comercial Alfa Ltda.\n\n"
    "O apresentante declarou endosso translativo ao Banco Beta S.A."
)
DOC = CheckDocumentInput(id="titulo", text=TITLE, source="titulo.txt")


def _by_claim(result):
    return {item.claim: item for item in result.results}


def test_wrong_date_is_refuted_with_exact_offsets() -> None:
    result = check_documents([DOC], claims=["O vencimento é em 15/03/2026."])
    item = result.results[0]
    assert item.verdict == "refuted"
    contradicting = [e for e in item.evidence if e.stance == "contradicts"]
    assert contradicting
    for evidence in contradicting:
        assert TITLE[evidence.start : evidence.end] == evidence.excerpt
        assert "10/03/2026" in evidence.excerpt


def test_claim_absent_from_documents_abstains_instead_of_false_support() -> None:
    item = check_documents([DOC], claims=["O título foi pago em janeiro."]).results[0]
    assert item.verdict is None
    assert item.status == "abstain/no_answer"
    assert all(e.stance != "supports" for e in item.evidence)


def test_exact_claim_is_supported_by_its_own_line() -> None:
    item = check_documents([DOC], claims=["O devedor é a empresa Comercial Alfa Ltda."]).results[0]
    assert item.verdict == "partially_supported"  # one independent source under ADR-002
    supporting = [e for e in item.evidence if e.stance == "supports"]
    assert [e.excerpt for e in supporting] == ["O devedor é a empresa Comercial Alfa Ltda."]


def test_two_independent_documents_are_needed_for_full_support() -> None:
    other = CheckDocumentInput(id="registro", text="Devedor: a empresa Comercial Alfa Ltda.")
    item = check_documents(
        [DOC, other], claims=["O devedor é a empresa Comercial Alfa Ltda."]
    ).results[0]
    assert item.verdict == "verified"  # two independent sources under ADR-002
    assert {e.document_id for e in item.evidence if e.stance == "supports"} == {
        "titulo",
        "registro",
    }


def test_passages_of_one_document_are_not_independent_sources() -> None:
    repeated = CheckDocumentInput(
        id="copia",
        text="\n".join(["O devedor é a empresa Comercial Alfa Ltda."] * 2),
    )
    item = check_documents(
        [repeated], claims=["O devedor é a empresa Comercial Alfa Ltda."]
    ).results[0]
    assert item.verdict == "partially_supported"


def test_no_relevant_passage_abstains() -> None:
    item = check_documents([DOC], claims=["Choveu muito ontem."]).results[0]
    assert item.status == "abstain/no_answer"
    assert item.abstention_reason == "no_relevant_passage"
    assert item.evidence == ()


def test_answer_is_decomposed_into_claims_verbatim() -> None:
    result = check_documents(
        [DOC], answer="O devedor é a empresa Comercial Alfa Ltda. O vencimento é em 15/03/2026."
    )
    assert [item.claim for item in result.results] == [
        "O devedor é a empresa Comercial Alfa Ltda.",
        "O vencimento é em 15/03/2026.",
    ]
    assert result.engine["claim_extractor"].startswith("claim_extractor.rule")


def test_trace_is_deterministic_and_bound_to_document_content() -> None:
    first = check_documents([DOC], claims=["O vencimento é em 15/03/2026."])
    second = check_documents([DOC], claims=["O vencimento é em 15/03/2026."])
    changed = check_documents(
        [CheckDocumentInput(id="titulo", text=TITLE.replace("4521", "4522"))],
        claims=["O vencimento é em 15/03/2026."],
    )
    assert first.trace_id == second.trace_id
    assert first.trace_id != changed.trace_id
    assert first.documents[0]["sha256"] != changed.documents[0]["sha256"]


def test_passages_have_exact_offsets() -> None:
    for passage in split_passages(DOC):
        assert TITLE[passage.start : passage.end] == passage.text
        assert passage.text == passage.text.strip()


def test_conservative_support_rule() -> None:
    complete = ConservativeStanceDetector.support_is_complete
    assert complete("O devedor é a empresa Comercial Alfa Ltda.", TITLE)
    assert not complete("O título foi pago em janeiro.", TITLE)
    assert not complete("O valor é de R$ 9.999,00.", TITLE)  # number absent


def test_api_check_end_to_end() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/check",
        json={
            "documents": [{"id": "titulo", "text": TITLE, "source": "titulo.txt"}],
            "answer": "O vencimento é em 15/03/2026. O título foi pago em janeiro.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "c1"
    assert body["trace_id"].startswith("chk_")
    assert body["documents"][0]["characters"] == len(TITLE)
    statuses = [item["status"] for item in body["results"]]
    assert statuses == ["refuted", "abstain/no_answer"]
    assert body["summary"] == {"abstain/no_answer": 1, "refuted": 1}


def test_api_check_rejects_invalid_requests() -> None:
    client = TestClient(app)
    doc = {"id": "a", "text": "texto"}
    assert client.post("/v1/check", json={"documents": [doc]}).status_code == 422
    assert (
        client.post(
            "/v1/check", json={"documents": [doc], "claims": ["x"], "answer": "y"}
        ).status_code
        == 422
    )
    assert (
        client.post("/v1/check", json={"documents": [doc, doc], "claims": ["x"]}).status_code == 422
    )
    assert (
        client.post(
            "/v1/check", json={"documents": [{"id": "a b", "text": "t"}], "claims": ["x"]}
        ).status_code
        == 422
    )
    assert client.post("/v1/check", json={"documents": [], "claims": ["x"]}).status_code == 422


def test_api_check_rejects_whitespace_only_answer() -> None:
    client = TestClient(app)
    doc = {"id": "a", "text": "Documento fictício."}
    for answer in ("   ", "\n\t "):
        response = client.post("/v1/check", json={"documents": [doc], "answer": answer})
        assert response.status_code == 422, response.text


def test_api_check_rejects_blank_document_text() -> None:
    client = TestClient(app)
    for text in ("", " ", "   ", "\n\t ", "\r\n"):
        response = client.post(
            "/v1/check",
            json={
                "documents": [{"id": "doc1", "text": text}],
                "claims": ["Afirmação fictícia."],
            },
        )
        assert response.status_code == 422, response.text
