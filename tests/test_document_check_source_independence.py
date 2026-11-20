"""Source independence: one text submitted several times is one source (ADR-002 §3).

Regression: the origin of a document was the SHA-256 of its raw text, so the same
text with different case, accents, final punctuation or a short prefix counted as a
second independent source and the claim reached "verified".
"""

from __future__ import annotations

from itertools import permutations

import pytest

from ayorai_attractor.verification.document_check import (
    CheckDocumentInput,
    check_documents,
    document_origins,
    normalize_for_identity,
)

CLAIM = "A receita da Vértice foi de 40 milhões de reais em 2024."
TEXT = "A receita da Vértice foi de 40 milhões de reais em 2024."


def _verdict(*texts: str) -> str | None:
    documents = [CheckDocumentInput(id=f"d{i}", text=text) for i, text in enumerate(texts)]
    return check_documents(documents, claims=[CLAIM]).results[0].verdict


@pytest.mark.parametrize(
    "copy",
    [
        TEXT,
        TEXT + " ",
        TEXT.upper(),
        TEXT.replace(".", "!"),
        "Nota: " + TEXT,
        TEXT.replace("é", "e").replace("õ", "o"),
    ],
)
def test_a_copy_of_the_same_text_is_not_a_second_source(copy: str) -> None:
    assert _verdict(TEXT, copy) == "partially_supported"


def test_independently_worded_sources_still_count_twice() -> None:
    assert (
        _verdict(
            "Segundo o balanço, a receita da Vértice foi de 40 milhões de reais em 2024.",
            "Em 2024, a Vértice teve receita de 40 milhões de reais, informou a agência.",
        )
        == "supported"  # two independent sources; client-supplied, so not "verified"
    )


def test_long_near_duplicate_with_a_few_changed_words_is_one_source() -> None:
    body = (
        "O relatório anual da Vértice informa que a receita foi de 40 milhões de reais em "
        "2024, com crescimento das vendas no varejo, expansão de lojas no Sul e aumento de "
        "margem operacional, segundo a diretoria financeira e os auditores independentes."
    )
    copy = body.replace("diretoria financeira", "diretoria de finanças")
    origins = document_origins(
        [CheckDocumentInput(id="a", text=body), CheckDocumentInput(id="b", text=copy)]
    )
    assert origins["a"] == origins["b"]


def test_a_short_text_quoted_inside_a_longer_document_is_the_same_origin() -> None:
    longer = "Reportagem de economia. " + TEXT + " A empresa não comentou o resultado."
    assert _verdict(TEXT, longer) == "partially_supported"


def test_same_topic_different_text_is_not_joined() -> None:
    origins = document_origins(
        [
            CheckDocumentInput(id="a", text="A receita da Vértice cresceu em 2024 no varejo."),
            CheckDocumentInput(id="b", text="A Vértice abriu três lojas no Sul em março."),
        ]
    )
    assert origins["a"] != origins["b"]


def test_origins_are_transitive_and_independent_of_document_order() -> None:
    texts = [TEXT, TEXT.upper(), "Nota: " + TEXT.upper(), "Outra fonte, outro texto sobre a sede."]
    reference = None
    for order in permutations(range(len(texts))):
        docs = [CheckDocumentInput(id=f"d{i}", text=texts[i]) for i in order]
        origins = document_origins(docs)
        groups = {frozenset(k for k, v in origins.items() if v == o) for o in origins.values()}
        named = {
            origin: frozenset(k for k, v in origins.items() if v == origin)
            for origin in origins.values()
        }
        assert groups == {frozenset({"d0", "d1", "d2"}), frozenset({"d3"})}
        if reference is None:
            reference = named
        assert named == reference  # same group names, whatever the order


def test_normalization_ignores_case_accents_punctuation_and_spaces() -> None:
    assert normalize_for_identity("  Receita: R$ 40,0 MILHÕES!  ") == "receita r 40 0 milhoes"


def test_engine_reports_the_independence_rule() -> None:
    result = check_documents([CheckDocumentInput(id="d", text=TEXT)], claims=[CLAIM])
    assert result.engine["source_independence"] == "normalized-content+word5-containment>=0.8"
