"""Synthetic-only tests for Phase 1b inference protocols. No benchmark data is used."""

from __future__ import annotations

import pytest

from scripts.benchmarks.phase1b.common import MODELS
from scripts.benchmarks.phase1b.protocols import (
    FACTCG_INSTRUCTION_TEMPLATE,
    PROTOCOLS,
    REQUIRED_KEYS,
    assert_all_fp32,
    chunk_factcg,
    chunk_minicheck,
    format_single_texts,
    get_protocol,
    sent_tokenize_with_newlines,
    validate_protocols,
)


def naive_sentences(text: str) -> list[str]:
    return [part.strip() + "." for part in text.split(".") if part.strip()]


def word_count(text: str) -> int:
    return len(text.split())


def test_every_model_has_a_complete_explicit_protocol() -> None:
    assert set(PROTOCOLS) == set(MODELS)
    for protocol in PROTOCOLS.values():
        assert all(key in protocol for key in REQUIRED_KEYS)
        assert protocol["sources"]
    validate_protocols()


def test_official_parameters_and_label_indices() -> None:
    minicheck = get_protocol("minicheck")
    factcg = get_protocol("factcg")
    mdeberta = get_protocol("mdeberta")
    assert (minicheck["max_length"], minicheck["chunk_size"], minicheck["overlap"]) == (
        2048,
        400,
        0,
    )
    assert (factcg["max_length"], factcg["chunk_size"], factcg["overlap"]) == (2048, 550, 0)
    assert (mdeberta["max_length"], mdeberta["chunk_size"], mdeberta["overlap"]) == (512, 384, 64)
    assert minicheck["support_index"] == 1 and minicheck["num_labels"] == 2
    assert factcg["support_index"] == 1 and factcg["num_labels"] == 2
    assert mdeberta["support_index"] == 0 and mdeberta["num_labels"] == 3
    assert minicheck["count_unit"] != factcg["count_unit"]
    assert minicheck["role"] == factcg["role"] == "official_reference"
    assert mdeberta["role"] == "ayorai_own_protocol"


def test_missing_or_invalid_protocol_fails_closed() -> None:
    with pytest.raises(ValueError):
        get_protocol("unknown-model")
    broken = {"x": dict(PROTOCOLS["minicheck"])}
    del broken["x"]["support_index"]
    with pytest.raises(ValueError):
        validate_protocols(broken)
    inverted = {"x": dict(PROTOCOLS["minicheck"], support_index=2)}
    with pytest.raises(ValueError):
        validate_protocols(inverted)


def test_minicheck_chunking_matches_official_rules() -> None:
    doc = "one two three. four five. six seven eight nine.\nten eleven."
    chunks = chunk_minicheck(
        doc, sent_tokenize=naive_sentences, count_tokens=word_count, chunk_size=5
    )
    assert chunks == ["one two three. four five.", "six seven eight nine.", "ten eleven."]
    oversized = chunk_minicheck(
        "a b c d e f g.", sent_tokenize=naive_sentences, count_tokens=word_count, chunk_size=3
    )
    assert oversized == ["a b c d e f g."]
    assert sent_tokenize_with_newlines("x. y.\nz.", naive_sentences) == ["x.", "y.", "\n", "z."]


def test_factcg_chunking_matches_official_rules() -> None:
    src = "one two three. four five. six seven eight nine."
    chunks = chunk_factcg(
        src, sent_tokenize=naive_sentences, count_words=word_count, max_chunk_size=5
    )
    assert chunks == ["one two three.\nfour five.", "six seven eight nine."]
    assert (
        chunk_factcg("", sent_tokenize=naive_sentences, count_words=word_count, max_chunk_size=5)
        == []
    )


def test_single_text_input_formats() -> None:
    assert format_single_texts(PROTOCOLS["minicheck"], ["doc"], "claim", "[SEP]") == [
        "doc[SEP]claim"
    ]
    factcg = format_single_texts(PROTOCOLS["factcg"], ["doc"], "claim", "[SEP]")
    assert factcg == [FACTCG_INSTRUCTION_TEMPLATE.format(text_a="doc", text_b="claim")]
    assert factcg[0].startswith("doc\n\nChoose your answer:")
    assert factcg[0].endswith("I think the answer is ")
    with pytest.raises(ValueError):
        format_single_texts(PROTOCOLS["mdeberta"], ["doc"], "claim", "[SEP]")


def test_fp32_guard_rejects_any_non_fp32_parameter() -> None:
    assert_all_fp32(["fp32", "fp32"], "fp32")
    with pytest.raises(RuntimeError):
        assert_all_fp32(["fp32", "fp16"], "fp32")
    with pytest.raises(RuntimeError):
        assert_all_fp32([], "fp32")
