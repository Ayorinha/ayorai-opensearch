"""Explicit, versioned inference protocols for Phase 1b (no heavy imports at module load).

Every value below is either copied from the official reference implementation at a pinned
commit (cited in ``sources``) or is an explicit AYORAI decision marked as such. Nothing is
inferred from model names or label strings at run time.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

MINICHECK_REF = "Liyan06/MiniCheck@b58b9fa69acbd1015ec970fa65dd752413a053d2"
FACTCG_REF = "derenlei/FactCG@41f185413312ed9b3904ec03963fe899693498e0"

# Copied verbatim from factcg/utils.py line 1 at FACTCG_REF.
FACTCG_INSTRUCTION_TEMPLATE = (
    "{text_a}\n\nChoose your answer: based on the paragraph above can we conclude that "
    '"{text_b}"?\n\nOPTIONS:\n- Yes\n- No\nI think the answer is '
)

REQUIRED_KEYS = (
    "protocol_name",
    "protocol_version",
    "role",
    "max_length",
    "chunk_size",
    "overlap",
    "count_unit",
    "splitter",
    "input_format",
    "truncation",
    "aggregation",
    "num_labels",
    "support_index",
    "sources",
)

PROTOCOLS: dict[str, dict[str, Any]] = {
    "mdeberta": {
        "protocol_name": "ayorai-mdeberta-regex-sentence-384-64",
        "protocol_version": "1",
        "role": "ayorai_own_protocol",
        "max_length": 512,
        "chunk_size": 384,
        "overlap": 64,
        "count_unit": "model_tokenizer_tokens",
        "splitter": "regex_sentence",
        "input_format": "pair_doc_claim",
        "truncation": "only_first",
        "aggregation": "max",
        "num_labels": 3,
        "support_index": 0,
        "sources": [
            "config.json@b5113eb38ab63efdd7f280f8c144ea8b13f978ce: "
            "id2label 0=entailment, 1=neutral, 2=contradiction",
            "max_length 512 = limit used for this model's training; chunking is an AYORAI decision",
        ],
    },
    "minicheck": {
        "protocol_name": "minicheck-deberta-official",
        "protocol_version": "1",
        "role": "official_reference",
        "max_length": 2048,
        "chunk_size": 400,
        "overlap": 0,
        "count_unit": "model_tokenizer_tokens",
        "splitter": "nltk_sent_tokenize_with_newlines",
        "input_format": "doc_eos_claim_single_text",
        "truncation": "longest_first",
        "aggregation": "max",
        "num_labels": 2,
        "support_index": 1,
        "sources": [
            f"{MINICHECK_REF} minicheck/inference.py:53 max_model_len=2048",
            f"{MINICHECK_REF} minicheck/minicheck.py:148 chunk_size=400 (non flan-t5)",
            f"{MINICHECK_REF} minicheck/inference.py:17-26,121-144 sentence chunking, no overlap",
            f"{MINICHECK_REF} minicheck/inference.py:235 doc + eos_token + claim, truncation=True",
            f"{MINICHECK_REF} minicheck/inference.py:217-218 class 1 = support, max over chunks",
        ],
    },
    "factcg": {
        "protocol_name": "factcg-deberta-official",
        "protocol_version": "1",
        "role": "official_reference",
        "max_length": 2048,
        "chunk_size": 550,
        "overlap": 0,
        "count_unit": "nltk_word_tokenize_words",
        "splitter": "nltk_sent_tokenize",
        "input_format": "factcg_instruction_template",
        "truncation": "only_first",
        "aggregation": "max",
        "num_labels": 2,
        "support_index": 1,
        "sources": [
            f"{FACTCG_REF} factcg/inference.py:97-140 chunking_src max_chunk_size=550 words",
            f"{FACTCG_REF} factcg/inference.py:191-201 instruction template, pad=eos, "
            "truncation only_first, max_length=2048",
            f"{FACTCG_REF} factcg/utils.py:1 INSTRUCTION_TEMPLATE",
            f"{FACTCG_REF} factcg/inference.py:89-92,169 class 1 = support, max over chunks",
            "arXiv 2501.17144 section 3: grounded = 1",
        ],
    },
}


def validate_protocols(protocols: dict[str, dict[str, Any]] = PROTOCOLS) -> None:
    for model_id, protocol in protocols.items():
        missing = [key for key in REQUIRED_KEYS if key not in protocol]
        if missing:
            raise ValueError(f"protocol for {model_id} is missing {missing}")
        if not 0 <= protocol["support_index"] < protocol["num_labels"]:
            raise ValueError(f"protocol for {model_id} has an invalid support_index")
        if protocol["chunk_size"] >= protocol["max_length"]:
            raise ValueError(f"protocol for {model_id} has chunk_size >= max_length")
        if protocol["aggregation"] != "max":
            raise ValueError(f"protocol for {model_id} has unsupported aggregation")
        if not protocol["sources"]:
            raise ValueError(f"protocol for {model_id} has no sources")


def get_protocol(model_id: str) -> dict[str, Any]:
    if model_id not in PROTOCOLS:
        raise ValueError("no explicit inference protocol for this model")
    return PROTOCOLS[model_id]


def sent_tokenize_with_newlines(text: str, sent_tokenize: Callable[[str], list[str]]) -> list[str]:
    """Port of MiniCheck minicheck/inference.py:17-26."""
    tokenized_text: list[str] = []
    for block in [sent_tokenize(block) for block in text.split("\n")]:
        tokenized_text.extend(block)
        tokenized_text.append("\n")
    return tokenized_text[:-1]


def chunk_minicheck(
    doc: str,
    *,
    sent_tokenize: Callable[[str], list[str]],
    count_tokens: Callable[[str], int],
    chunk_size: int,
) -> list[str]:
    """Port of MiniCheck minicheck/inference.py:121-144 (DeBERTa branch)."""

    def chunks(sentences: list[str], limit: int) -> Iterable[str]:
        current_chunk: list[str] = []
        current_token_count = 0
        for sentence in sentences:
            sentence_count = count_tokens(sentence)
            if current_token_count + sentence_count > limit:
                yield " ".join(current_chunk)
                current_chunk = [sentence]
                current_token_count = sentence_count
            else:
                current_chunk.append(sentence)
                current_token_count += sentence_count
        if current_chunk:
            yield " ".join(current_chunk)

    doc_sents = sent_tokenize_with_newlines(doc, sent_tokenize) or [""]
    doc_chunks = [chunk.replace(" \n ", "\n").strip() for chunk in chunks(doc_sents, chunk_size)]
    return [chunk for chunk in doc_chunks if chunk != ""]


def chunk_factcg(
    src: str,
    *,
    sent_tokenize: Callable[[str], list[str]],
    count_words: Callable[[str], int],
    max_chunk_size: int,
) -> list[str]:
    """Port of FactCG factcg/inference.py:97-140 (only sentence text is used downstream)."""
    chunks: list[str] = []
    chunk_size = 0
    chunk = ""
    for sentence in sent_tokenize(src):
        token_count = count_words(sentence)
        if chunk_size + token_count <= max_chunk_size:
            chunk = "\n".join([chunk, sentence]).strip("\n")
            chunk_size += token_count
        else:
            chunks.append(chunk.strip("\n"))
            chunk = sentence
            chunk_size = token_count
    if chunk_size > 0:
        chunks.append(chunk.replace(" \n ", "\n").strip("\n").strip())
    return chunks


def format_single_texts(
    protocol: dict[str, Any], chunks: list[str], claim: str, eos: str
) -> list[str]:
    """Single-sequence inputs for protocols that do not use pair encoding."""
    if protocol["input_format"] == "doc_eos_claim_single_text":
        return [eos.join([chunk, claim]) for chunk in chunks]
    if protocol["input_format"] == "factcg_instruction_template":
        return [FACTCG_INSTRUCTION_TEMPLATE.format(text_a=chunk, text_b=claim) for chunk in chunks]
    raise ValueError("protocol uses pair encoding, not single texts")


def assert_all_fp32(dtypes: Iterable[Any], fp32: Any) -> None:
    """Fail closed if any parameter dtype differs from FP32; never convert silently."""
    seen = False
    for dtype in dtypes:
        seen = True
        if dtype != fp32:
            raise RuntimeError("model has non-FP32 parameters; refusing to run")
    if not seen:
        raise RuntimeError("model exposes no parameters to validate")


validate_protocols()
