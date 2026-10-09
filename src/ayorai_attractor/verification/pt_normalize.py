"""Deterministic Portuguese normalisation for rule-based stance (detector v6).

Brazilian legal and institutional texts write quantities in words ("vinte
anos"), duplicate them ("40 (quarenta) anos"), use fractions ("um terço",
"metade", "de um a dois terços") and multipliers ("o dobro", "até o triplo").
The rule detector only compares digit facts, so these quantities were invisible
and contradictions passed as support. This module turns them into comparable
facts without any model.
"""

from __future__ import annotations

import re
import unicodedata
from fractions import Fraction

_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]+", re.UNICODE)

_UNITS = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
}
_TEENS = {
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
}
_TENS = {
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "cinqüenta": 50,
    "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90,
}
_HUNDREDS = {
    "cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300,
    "trezentas": 300, "quatrocentos": 400, "quatrocentas": 400, "quinhentos": 500,
    "quinhentas": 500, "seiscentos": 600, "seiscentas": 600, "setecentos": 700,
    "setecentas": 700, "oitocentos": 800, "oitocentas": 800, "novecentos": 900,
    "novecentas": 900,
}
_NUMBER_WORDS = {**_UNITS, **_TEENS, **_TENS, **_HUNDREDS}
# "um"/"uma" are also articles; they become 1 only before a unit of measure.
_UNIT_NOUNS = frozenset(
    {"ano", "anos", "mês", "mes", "meses", "dia", "dias", "hora", "horas", "vez", "vezes"}
)

_DENOMINATORS = {
    "meio": 2, "terço": 3, "terco": 3, "quarto": 4, "quinto": 5, "sexto": 6,
    "sétimo": 7, "setimo": 7, "oitavo": 8, "nono": 9, "décimo": 10, "decimo": 10,
    "vigésimo": 20, "vigesimo": 20, "trigésimo": 30, "trigesimo": 30,
}
_DENOMINATOR_PATTERN = "|".join(
    sorted({f"{name}s?" for name in _DENOMINATORS}, key=len, reverse=True)
)
_NUMERATOR_PATTERN = r"um|uma|dois|duas|três|tres|quatro|cinco|\d"
_FRACTION_RANGE_RE = re.compile(
    rf"\bde\s+(?P<a>{_NUMERATOR_PATTERN})\s+a\s+(?P<b>{_NUMERATOR_PATTERN})\s+"
    rf"(?P<den>{_DENOMINATOR_PATTERN})\b",
    re.IGNORECASE,
)
_FRACTION_RE = re.compile(
    rf"\b(?P<num>{_NUMERATOR_PATTERN})\s+(?P<den>{_DENOMINATOR_PATTERN})\b",
    re.IGNORECASE,
)
_HALF_RE = re.compile(r"\bmetade\b", re.IGNORECASE)
_MULTIPLIERS = {"dobro": 2, "triplo": 3, "quádruplo": 4, "quadruplo": 4, "quíntuplo": 5}
_MULTIPLIER_RE = re.compile(
    r"\b(?P<word>dobro|triplo|qu[áa]druplo|quíntuplo)\b", re.IGNORECASE
)
# "40 (quarenta)" -> "40": the legal duplicate of a number is not a second fact.
_DUPLICATE_RE = re.compile(r"\b(?P<digits>\d+)\s*\((?P<words>[a-zà-ÿ\s]+)\)", re.IGNORECASE)

QuantityFact = tuple[str, str, str]


def strip_accents(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn"
    )


def _numerator(token: str) -> int:
    lowered = token.casefold()
    return int(lowered) if lowered.isdigit() else _UNITS[lowered]


def _denominator(token: str) -> int:
    lowered = token.casefold()
    return _DENOMINATORS[lowered[:-1] if lowered.endswith("s") else lowered]


def extract_quantities(text: str) -> tuple[list[QuantityFact], str]:
    """Return (fraction/multiplier facts, text with those phrases removed).

    Facts are (raw value, unit, attribute) with unit `fraction` or `multiplier`;
    raw values are exact rationals such as "2/3".
    """
    facts: list[QuantityFact] = []

    def take_range(match: re.Match[str]) -> str:
        den = _denominator(match.group("den"))
        for side in ("a", "b"):
            value = Fraction(_numerator(match.group(side)), den)
            facts.append((str(value), "fraction", "fraction"))
        return " "

    def take_fraction(match: re.Match[str]) -> str:
        value = Fraction(_numerator(match.group("num")), _denominator(match.group("den")))
        facts.append((str(value), "fraction", "fraction"))
        return " "

    def take_half(_: re.Match[str]) -> str:
        facts.append(("1/2", "fraction", "fraction"))
        return " "

    def take_multiplier(match: re.Match[str]) -> str:
        word = strip_accents(match.group("word").casefold())
        value = {strip_accents(k): v for k, v in _MULTIPLIERS.items()}[word]
        facts.append((str(value), "multiplier", "multiplier"))
        return " "

    remaining = _FRACTION_RANGE_RE.sub(take_range, text)
    remaining = _FRACTION_RE.sub(take_fraction, remaining)
    remaining = _HALF_RE.sub(take_half, remaining)
    remaining = _MULTIPLIER_RE.sub(take_multiplier, remaining)
    return facts, remaining


def _compose(words: list[str]) -> int | None:
    total = 0
    last = None
    for word in words:
        value = _NUMBER_WORDS[word]
        if last is not None and value >= last:
            return None
        total += value
        last = value
    return total


def normalize_numerals(text: str) -> str:
    """Rewrite Portuguese number words as digits and drop legal duplicates."""
    text = _DUPLICATE_RE.sub(lambda m: m.group("digits"), text)
    words = list(_WORD_RE.finditer(text))
    pieces: list[str] = []
    cursor = 0
    index = 0
    while index < len(words):
        word = words[index].group(0).casefold()
        if word not in _NUMBER_WORDS:
            index += 1
            continue
        run = [index]
        probe = index + 1
        while (
            probe + 1 < len(words)
            and words[probe].group(0).casefold() == "e"
            and words[probe + 1].group(0).casefold() in _NUMBER_WORDS
            and text[words[run[-1]].end() : words[probe + 1].start()].strip() == "e"
        ):
            run.append(probe + 1)
            probe += 2
        tokens = [words[i].group(0).casefold() for i in run]
        value = _compose(tokens)
        following = words[run[-1] + 1].group(0).casefold() if run[-1] + 1 < len(words) else ""
        is_article = tokens == ["um"] or tokens == ["uma"]
        # "cento" is a number only inside "cento e ..." ("12 por cento" is a percent).
        bare_cento = tokens == ["cento"]
        if value is None or bare_cento or (is_article and following not in _UNIT_NOUNS):
            index += 1
            continue
        start, end = words[run[0]].start(), words[run[-1]].end()
        pieces.append(text[cursor:start])
        pieces.append(str(value))
        cursor = end
        index = run[-1] + 1
    pieces.append(text[cursor:])
    return "".join(pieces)


_ENTITY_STOP = frozenset(
    {
        "o", "a", "os", "as", "pelo", "pela", "pelos", "pelas", "no", "na", "nos", "nas",
        "em", "de", "do", "da", "dos", "das", "segundo", "para", "com", "ao", "aos", "se",
        "um", "uma", "the", "in", "of", "for", "by", "nao", "não", "art", "lei",
    }
)
_CAPITAL_RE = re.compile(r"\b[A-ZÀ-Ý][\wÀ-ÿ]*|\b(?:de|do|da|dos|das|e|of)\b")


# Generic heads that do not identify an actor on their own ("Empresa X").
GENERIC_NAME_WORDS = frozenset(
    {"empresa", "company", "companhia", "grupo", "group", "the", "corp", "inc", "ltda", "sa"}
)


def named_entities(text: str) -> set[str]:
    """Multi-word capitalised names (institutions, programmes, places).

    Leading function words are dropped; single capitalised words are ignored
    because sentence-initial words are capitalised too.
    """
    found: set[str] = set()
    run: list[str] = []
    last_end = -1
    for match in _CAPITAL_RE.finditer(text):
        token = match.group(0)
        contiguous = last_end >= 0 and text[last_end : match.start()].strip() == ""
        if not contiguous:
            _flush(run, found)
            run = []
        run.append(token)
        last_end = match.end()
    _flush(run, found)
    return found


def _flush(run: list[str], found: set[str]) -> None:
    while run and (run[0].casefold() in _ENTITY_STOP or not run[0][:1].isupper()):
        run.pop(0)
    while run and not run[-1][:1].isupper():
        run.pop()
    capitals = [token for token in run if token[:1].isupper()]
    if len(capitals) >= 2:
        found.add(strip_accents(" ".join(run).casefold()))
