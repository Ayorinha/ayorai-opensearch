"""Every relevant document reaches adjudication, however many others outrank it.

Regression: with a global top-3 passage selection, four supporting documents hid a
fifth that explicitly contradicted the claim, and /v1/check returned "verified".
"""

from __future__ import annotations

from itertools import permutations

from ayorai_attractor.verification.document_check import (
    ENGINE_VERSION,
    TOP_K_PASSAGES,
    CheckDocumentInput,
    check_documents,
    content_tokens,
    rank_passages,
    split_passages,
)

CLAIM = "A receita da Vértice foi de 40 milhões de reais em 2024."
SUPPORTING = [
    f"Segundo o veículo {index}, a receita da Vértice foi de 40 milhões de reais em 2024."
    for index in range(4)
]
CONTRADICTING = (
    "Em relatório auditado, a receita consolidada da Vértice em 2024 foi de 70 milhões "
    "de reais, e não 40 milhões como circulou."
)


def _documents(texts: list[str]) -> list[CheckDocumentInput]:
    return [CheckDocumentInput(id=f"d{index}", text=text) for index, text in enumerate(texts)]


def _check(texts: list[str]):
    return check_documents(_documents(texts), claims=[CLAIM]).results[0]


def test_contradiction_outranked_by_supporting_documents_is_adjudicated() -> None:
    for texts in (SUPPORTING + [CONTRADICTING], [CONTRADICTING] + SUPPORTING):
        item = _check(texts)
        assert item.verdict == "conflicting"
        stances = {e.document_id: e.stance for e in item.evidence}
        contradicting_id = f"d{texts.index(CONTRADICTING)}"
        assert stances[contradicting_id] == "contradicts"
        assert len(stances) == 5  # every document is represented


def test_verdict_is_invariant_to_document_order() -> None:
    texts = SUPPORTING + [CONTRADICTING]
    verdicts = set()
    for order in permutations(range(len(texts))):
        documents = [CheckDocumentInput(id=f"d{i}", text=texts[i]) for i in order]
        verdicts.add(check_documents(documents, claims=[CLAIM]).results[0].verdict)
    assert verdicts == {"conflicting"}


def test_every_supporting_document_counts_beyond_the_top_k() -> None:
    item = _check(SUPPORTING)
    # Client-supplied documents cap at "supported" (ADR-002 §2); all four still count.
    assert item.verdict == "supported"
    assert {e.document_id for e in item.evidence if e.stance == "supports"} == {
        "d0",
        "d1",
        "d2",
        "d3",
    }


def test_unrelated_documents_are_not_added() -> None:
    item = _check(SUPPORTING[:1] + ["Texto sobre outro assunto, sem termos em comum."])
    assert {e.document_id for e in item.evidence} == {"d0"}


def test_rank_passages_default_is_the_plain_global_top_k() -> None:
    passages = [p for doc in _documents(SUPPORTING + [CONTRADICTING]) for p in split_passages(doc)]
    plain = rank_passages(CLAIM, passages, TOP_K_PASSAGES)
    assert len(plain) == TOP_K_PASSAGES
    covered = rank_passages(CLAIM, passages, TOP_K_PASSAGES, per_document=True)
    assert covered[:TOP_K_PASSAGES] == plain
    assert {p.document_id for p in covered} == {f"d{i}" for i in range(5)}
    tokens = [content_tokens(p.text) for p in passages]
    assert rank_passages(CLAIM, passages, TOP_K_PASSAGES, tokens, per_document=True) == covered


def test_one_passage_per_extra_document_and_engine_version_reports_the_rule() -> None:
    long_doc = " ".join(SUPPORTING)  # four matching sentences in one document
    passages = [p for doc in _documents([long_doc] * 1 + SUPPORTING) for p in split_passages(doc)]
    covered = rank_passages(CLAIM, passages, 1, per_document=True)
    per_doc = [p.document_id for p in covered]
    assert len(per_doc) == len(set(per_doc))
    result = check_documents(_documents(SUPPORTING), claims=[CLAIM])
    assert ENGINE_VERSION == "document-check-5"
    assert result.engine["passage_selection"].startswith(
        f"lexical-top{TOP_K_PASSAGES}+best-per-document"
    )


def test_selection_is_exact_one_extra_passage_per_uncovered_document_in_relevance_order() -> None:
    # Paragraphs are separate passages. "a" holds the two strongest passages (tied,
    # so document order breaks the tie), so the global top-2 is a1, a2; "b" and "c"
    # each add only their best passage, and the result is ordered by relevance
    # (c's best outranks b's best), not by document.
    texts = {
        "a": "A receita da Vértice foi de 40 milhões de reais em 2024.\n\n"
        "Receita da Vértice: 40 milhões de reais em 2024.\n\n"
        "A Vértice tem sede em Curitiba.",
        "b": "A Vértice divulgou números.\n\nA Vértice abriu filiais e contratou.",
        "c": "Vértice teve receita de 40 milhões.\n\nA Vértice mudou de sede.",
    }
    documents = [CheckDocumentInput(id=key, text=value) for key, value in texts.items()]
    passages = [p for doc in documents for p in split_passages(doc)]
    plain = rank_passages(CLAIM, passages, 2)
    assert [(p.document_id, p.text[:12]) for p in plain] == [
        ("a", "A receita da"),
        ("a", "Receita da V"),
    ]
    covered = rank_passages(CLAIM, passages, 2, per_document=True)
    assert [p.document_id for p in covered] == ["a", "a", "c", "b"]
    assert covered[2].text == "Vértice teve receita de 40 milhões."
    assert covered[3].text == "A Vértice divulgou números."
