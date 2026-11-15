"""The per-request caches of /v1/check must not change any result."""

import random
import unicodedata

import pytest

from ayorai_attractor.verification.document_check import (
    CheckDocumentInput,
    content_tokens,
    rank_passages,
    split_passages,
)
from ayorai_attractor.verification.excerpt import locate_excerpt, normalize_source

_WORDS = (
    "empresa atlas fundada receita lucro cresceu caiu não milhões 2019 2020 "
    "São Paulo José ação ﬁnal Ångström café ñandú"
).split()


def _sentence(rng: random.Random) -> str:
    text = " ".join(rng.choice(_WORDS) for _ in range(rng.randint(3, 14)))
    text += f" em {rng.randint(2015, 2026)}."
    return unicodedata.normalize(rng.choice(["NFC", "NFD", "NFKD"]), text)


@pytest.mark.parametrize("seed", range(20))
def test_precomputed_passage_tokens_rank_identically(seed: int) -> None:
    rng = random.Random(seed)
    document = CheckDocumentInput(
        id="d1", text=" ".join(_sentence(rng) for _ in range(30)), source=None, url=None
    )
    passages = split_passages(document)
    tokens = [content_tokens(passage.text) for passage in passages]
    for _ in range(5):
        claim = _sentence(rng)
        assert rank_passages(claim, passages, 3, tokens) == rank_passages(claim, passages, 3)


def test_misaligned_passage_tokens_are_rejected() -> None:
    document = CheckDocumentInput(id="d1", text="Atlas cresceu. Atlas caiu.", source=None, url=None)
    passages = split_passages(document)
    with pytest.raises(ValueError, match="align"):
        rank_passages("Atlas cresceu", passages, 3, [])


@pytest.mark.parametrize("seed", range(20))
def test_precomputed_normalized_source_locates_identically(seed: int) -> None:
    rng = random.Random(seed)
    source = " ".join(_sentence(rng) for _ in range(10))
    normalized = normalize_source(source)
    for _ in range(10):
        start = rng.randrange(len(source))
        excerpt = source[start : start + rng.randint(1, 40)]
        for candidate in (excerpt, unicodedata.normalize("NFC", excerpt), "ausente"):
            assert locate_excerpt(source, candidate, normalized) == locate_excerpt(
                source, candidate
            )


@pytest.mark.parametrize("seed", range(10))
def test_source_text_locates_identically_and_maps_once(seed: int, monkeypatch) -> None:
    from ayorai_attractor.verification import excerpt as module

    rng = random.Random(seed)
    plain = " ".join(_sentence(rng) for _ in range(10))
    cached = module.SourceText(plain)
    assert cached == plain
    calls = 0
    original = module._nfc_with_map

    def counting(text: str) -> module.NormalizedSource:
        nonlocal calls
        calls += 1
        return original(text)

    expected = [
        locate_excerpt(plain, plain[i : i + 25])
        for i in range(0, len(plain), max(1, len(plain) // 8))
    ]
    monkeypatch.setattr(module, "_nfc_with_map", counting)
    actual = [
        locate_excerpt(cached, plain[i : i + 25])
        for i in range(0, len(plain), max(1, len(plain) // 8))
    ]
    assert actual == expected
    assert calls == 1
