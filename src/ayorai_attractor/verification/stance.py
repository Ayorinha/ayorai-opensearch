from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .extraction import ComponentProvenance, ExtractedClaim
from .models import Evidence, Stance, StanceEdge
from .numeric import (
    DEFAULT_RELATIVE_TOLERANCE,
    NumericLocale,
    parse_number,
    relative_difference,
)
from .pt_normalize import (
    GENERIC_NAME_WORDS,
    extract_quantities,
    named_entities,
    normalize_numerals,
    strip_accents,
)


class LLMStancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    evidence_id: str = Field(min_length=1)
    stance: Literal["supports", "contradicts", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)


_NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+|[.,]\d{3})*(?:\s*%)?")
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
# A number introduced as the baseline of a comparison ("caiu para 31, contra 40
# no ano anterior", "de 40 para 31", "31, versus 40", "from 40 to 31") describes
# another period or state, so it neither confirms nor contradicts a claim.
# "contra"/"ante"/"versus" count only after a comma, a number or at the start
# of a clause ("venceu ações contra 3 operadoras" is not a comparison); "from"
# and "de" only in "from N to M" / "de N para M"; "than" never ("more than 40"
# is a bound). Calendar years are time anchors, never masked.
_MONEY_PREFIX = r"(?:(?:r\$|us\$|\$|€|usd|brl|eur)\s*)?"
_BASELINE_VALUE = r"(?P<number>[-+]?\d+(?:[.,]\d+)*)"
_BASELINE_NUMBER_RE = re.compile(
    r"(?P<marker>"
    r"(?:(?:^|[,;(])\s*|(?<=\d)\s+|(?<=\d\s)\w+\s+|(?<=%)\s+)"
    r"(?:contra|ante|versus|vs\.?)\s+(?:(?:os|as|o|a|the)\s+)?"
    + _MONEY_PREFIX
    + r"|\b(?:comparad[oa]s?\s+(?:a|com|aos?|às?)|compared\s+(?:to|with))\s+"
    r"(?:(?:os|as|o|a|the)\s+)?"
    + _MONEY_PREFIX
    + r"|\b(?:de|from)\s+"
    + _MONEY_PREFIX
    + r"(?=\d+(?:[.,]\d+)*[^.;:!?\d]{0,40}?"
    r"\b(?:para|to)\s+" + _MONEY_PREFIX + r"\d)"
    r")" + _BASELINE_VALUE,
    re.IGNORECASE | re.MULTILINE,
)
_CALENDAR_YEAR_RE = re.compile(r"(?:19|20)\d\d")
_YEAR_TOKEN_RE = re.compile(r"\b(?:19|20)\d\d\b")
_BASELINE_CLAUSE_END_RE = re.compile(r"[.;:!?,]")
_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
# Negation is language dependent. In Portuguese "no"/"na"/"nos"/"nas" are
# contractions of em + article ("no fim de 2025") and "sem" ("sem custo")
# does not negate the predicate, so neither counts as negation there.
_NEGATION_TOKENS_EN = frozenset({"not", "no", "didn't", "doesn't", "never"})
_NEGATION_TOKENS_PT = frozenset(
    {"não", "nao", "nunca", "jamais", "nem", "nenhum", "nenhuma", "ninguém", "ninguem"}
)
_NEGATION_TOKENS = _NEGATION_TOKENS_EN | _NEGATION_TOKENS_PT
# Sentential negation: an operator that declares the whole proposition false
# ("É falso que X", "It is false that X") has no negator token. Each match flips
# the polarity once; a negator directly before it ("Não é falso que X") cancels
# it, and the matched words are removed before the token check so that the
# negator is not counted again. Reported denials ("negou que") are not operators.
_SENTENTIAL_NEGATION_PT = re.compile(
    r"(?P<negated>\b(?:não|nao)\s+)?\bé\s+"
    r"(?:falso|falsa|incorreto|incorreta|inverídico|inverídica|mentira)\s+"
    r"(?:afirmar\s+que|dizer\s+que|que)\b",
    re.IGNORECASE,
)
_SENTENTIAL_NEGATION_EN = re.compile(
    r"\bit\s+is\s+(?P<negated>not\s+)?(?:false|untrue|incorrect)\s+(?:to\s+say\s+)?that\b",
    re.IGNORECASE,
)
# Postposed form: "a notícia de que X é falsa" denies X; "... não é falsa"
# affirms it. The proposition X is the operator's scope.
_SENTENTIAL_NEGATION_POST_PT = re.compile(
    r"\b(?:a|o)\s+(?:afirmação|afirmacao|informação|informacao|notícia|noticia|alegação"
    r"|alegacao|boato|rumor|versão|versao|declaração|declaracao)\s+de\s+que\s+"
    r"(?P<scope>[^.;:!?]{1,300}?)\s+(?P<negated>(?:não|nao)\s+)?(?:é|era|foi)\s+"
    r"(?:falso|falsa|incorreto|incorreta|inverídico|inverídica|mentiroso|mentirosa"
    r"|infundado|infundada)\b",
    re.IGNORECASE,
)
# An operator only reaches the end of its clause: "É falso que A faliu. B" does
# not deny B, and neither does "É falso que A faliu porque B". When the claim is
# known, an operator counts only if its clause holds at least half of the
# claim's content tokens.
_CLAUSE_END_RE = re.compile(
    r"[.;:!?]|,\s+(?:e|mas|porém|porem|enquanto|and|but|while)\b"
    r"|\b(?:porque|pois|já\s+que|ja\s+que|uma\s+vez\s+que|embora|enquanto|mas|porém|porem"
    r"|contudo|todavia|because|although|whereas)\b",
    re.IGNORECASE,
)
_OPERATOR_SCOPE_COVERAGE = 0.5
# Sentence boundary for token negation: "A Vértice não faliu. A receita foi de 40
# milhões" negates another proposition. A boundary needs whitespace after the
# mark, so decimals and thousands separators ("1.200", "1,2") never split.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.;!?])\s+")
# A sentence made only of denial words ("Isso não é verdade.", "Não procede.",
# "That is not true.") refers back to the previous sentence: it still counts.
# "A empresa não comentou." has content of its own and does not.
_ANAPHORIC_DENIAL_WORDS = frozenset(
    {
        "isso",
        "isto",
        "aquilo",
        "essa",
        "esta",
        "informação",
        "informacao",
        "é",
        "e",
        "foi",
        "era",
        "verdade",
        "verdadeiro",
        "verdadeira",
        "procede",
        "correto",
        "correta",
        "certo",
        "certa",
        "bem",
        "assim",
        "o",
        "a",
        "that",
        "this",
        "it",
        "is",
        "was",
        "true",
        "correct",
        "so",
        "the",
        "case",
    }
)
# Reported denial: the document says that someone denied the proposition. It
# neither asserts the proposition nor establishes that it is false.
_REPORTED_DENIAL_RE = re.compile(
    r"\b(?:negou|nega|negam|negaram|negava|negavam|desmentiu|desmente|desmentem"
    r"|desmentiram|contestou|contesta|contestam|contestaram|refutou|refuta|refutaram"
    r"|denied|denies|deny|disputed|disputes|refuted|refutes)\s+(?:que|that)\b",
    re.IGNORECASE,
)
# Portuguese-only function words used solely to decide whether "no" is English.
_PT_FUNCTION_WORDS = frozenset(
    {"de", "do", "da", "dos", "das", "um", "os", "as", "ao", "aos", "pelo", "pela", "também"}
)

_PT_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_PT_MONTH_PATTERN = "|".join(sorted(_PT_MONTHS, key=len, reverse=True))
_PT_DAY_DATE_RE = re.compile(
    rf"\b(?P<day>\d{{1,2}})(?:º|°|o)?\s+de\s+(?P<month>{_PT_MONTH_PATTERN})\s+de\s+(?P<year>\d{{4}})\b",
    re.IGNORECASE,
)
_PT_MONTH_DATE_RE = re.compile(
    rf"\b(?P<month>{_PT_MONTH_PATTERN})\s+de\s+(?P<year>\d{{4}})\b",
    re.IGNORECASE,
)
_SLASH_DATE_RE = re.compile(r"\b(?P<a>\d{1,2})/(?P<b>\d{1,2})/(?P<year>\d{4})\b")

# Directional predicates: (axis, polarity). Opposite polarity on the same axis
# for the same proposition is a contradiction even when the numbers coincide.
_DIRECTION_TERMS: dict[str, tuple[str, int]] = {
    **dict.fromkeys(
        (
            "subiu",
            "subiram",
            "sobe",
            "sobem",
            "subir",
            "aumentou",
            "aumentaram",
            "aumenta",
            "aumentam",
            "aumentar",
            "aumento",
            "cresceu",
            "cresceram",
            "cresce",
            "crescem",
            "crescer",
            "crescimento",
            "increased",
            "increase",
            "increases",
            "rose",
            "rise",
            "rises",
            "grew",
            "grow",
            "grows",
        ),
        ("change", 1),
    ),
    **dict.fromkeys(
        (
            "caiu",
            "caíram",
            "cairam",
            "cai",
            "caem",
            "cair",
            "queda",
            "diminuiu",
            "diminuíram",
            "diminuiram",
            "diminui",
            "diminuem",
            "diminuir",
            "diminuição",
            "diminuicao",
            "reduziu",
            "reduziram",
            "reduz",
            "reduzem",
            "redução",
            "reducao",
            "encolheu",
            "encolheram",
            "encolhe",
            "encolhem",
            "decreased",
            "decrease",
            "decreases",
            "fell",
            "fall",
            "falls",
            "declined",
            "decline",
            "declines",
            "dropped",
            "drop",
            "drops",
        ),
        ("change", -1),
    ),
    **dict.fromkeys(
        (
            "aprovou",
            "aprovaram",
            "aprova",
            "aprovam",
            "aprovado",
            "aprovada",
            "aprovados",
            "aprovadas",
            "aprovação",
            "aprovacao",
            "approved",
            "approves",
            "approve",
        ),
        ("approval", 1),
    ),
    **dict.fromkeys(
        (
            "rejeitou",
            "rejeitaram",
            "rejeita",
            "rejeitam",
            "rejeitado",
            "rejeitada",
            "rejeitados",
            "rejeitadas",
            "rejeição",
            "rejeicao",
            "reprovou",
            "reprovaram",
            "reprovado",
            "reprovada",
            "vetou",
            "vetaram",
            "vetado",
            "vetada",
            "rejected",
            "rejects",
            "reject",
        ),
        ("approval", -1),
    ),
}
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "for",
        "in",
        "on",
        "at",
        "to",
        "was",
        "were",
        "is",
        "are",
        "reported",
        "reports",
        "year",
        "fiscal",
        "de",
        "da",
        "do",
        "e",
        "em",
        "no",
        "na",
        "foi",
        "era",
        "é",
    }
)
_UNIT_WORDS = frozenset(
    {
        "usd",
        "eur",
        "brl",
        "ms",
        "million",
        "millions",
        "billion",
        "billions",
        "employees",
        "people",
        "customers",
        "offices",
        "percent",
        "rate",
        "year",
        "mil",
        "milhão",
        "milhões",
        "bilhão",
        "bilhões",
    }
)
_PT_MARKERS = frozenset(
    {
        "não",
        "nao",
        "uma",
        "para",
        "com",
        "que",
        "foi",
        "são",
        "sao",
        "empresa",
        "receita",
        "ano",
        "dos",
        "das",
        "em",
        "por",
    }
)
_ENTITY_PATTERN = r"\b(?:company|empresa)\s+(?P<name>[A-Za-zÀ-ÿ][\wÀ-ÿ-]*)\b"
_ENTITY_RE = re.compile(
    r"\b(?:company|empresa)\s+(?P<name>[A-Za-zÀ-ÿ][\wÀ-ÿ-]*)\b",
    re.IGNORECASE | re.UNICODE,
)
_EN_MARKERS = frozenset(
    {
        "the",
        "was",
        "were",
        "with",
        "that",
        "company",
        "revenue",
        "year",
        "from",
        "for",
        "and",
        "not",
        "this",
        "reported",
    }
)


def _language_scores(text: str) -> tuple[int, int]:
    tokens = {token.casefold() for token in _TOKEN_RE.findall(text)}
    pt = len(tokens & _PT_MARKERS) + sum(char in text for char in "ãõáéíóúç")
    en = len(tokens & _EN_MARKERS)
    return pt, en


def detect_language(text: str) -> str:
    pt, en = _language_scores(text)
    return "pt" if pt > en else "en"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _has_negation(text: str, claim_tokens: frozenset[str] | None = None) -> bool:
    """Return True when the text negates its predicate.

    Portuguese negators always count. The English-only token "no" counts only
    when the text is more English than Portuguese, so Portuguese contractions
    ("no fim de 2025") and "sem" ("sem custo adicional") are not negation.
    A sentential operator ("É falso que X") flips the result. With
    ``claim_tokens`` an operator counts only when its clause covers the claim.
    Text without a counted operator is classified exactly as before; otherwise
    every operator's own words (including the "não" of "não é falso que") are
    removed before the token check, and only counted operators flip.
    """
    operators = 0
    flips = 0

    def _remove(match: re.Match[str]) -> str:
        nonlocal operators, flips
        postposed = "scope" in match.re.groupindex
        # A postposed operator wraps its proposition: keep the proposition so
        # that a negation inside it is still seen by the token check.
        kept = f" {match.group('scope')} " if postposed else " "
        scope = match.group("scope") if postposed else _clause_after(match.string, match.end())
        if claim_tokens is not None and not _covers_claim(scope, claim_tokens):
            return kept
        operators += 1
        if match.group("negated") is None:
            flips += 1
        return kept

    remainder = text
    for pattern in (
        _SENTENTIAL_NEGATION_POST_PT,
        _SENTENTIAL_NEGATION_PT,
        _SENTENTIAL_NEGATION_EN,
    ):
        remainder = pattern.sub(_remove, remainder)
    if operators == 0:
        return _has_claim_token_negation(text, claim_tokens)
    return (flips % 2 == 1) != _has_claim_token_negation(remainder, claim_tokens)


def _has_claim_token_negation(text: str, claim_tokens: frozenset[str] | None) -> bool:
    """Token negation, limited to the sentences that state the claim.

    Without ``claim_tokens``, or for a single sentence, this is exactly the token
    check. In a multi-sentence excerpt a negator counts only in a sentence that
    covers the claim, or in a sentence made only of denial words that refers back
    to the previous one ("Isso não é verdade.").
    """
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s]
    if claim_tokens is None or len(sentences) < 2:
        return _has_token_negation(text)
    for sentence in sentences:
        if not _has_token_negation(sentence):
            continue
        if _covers_claim(sentence, claim_tokens):
            return True
        tokens = {token.casefold() for token in _TOKEN_RE.findall(sentence)}
        if tokens - _NEGATION_TOKENS <= _ANAPHORIC_DENIAL_WORDS:
            return True
    return False


# Non-assertive framing: the sentence that states the claim presents it as a
# possibility, estimate, projection, rumour, hypothesis or open question, so it
# neither establishes nor refutes it. Checked only in sentences covering the claim.
_NON_ASSERTIVE_RE = re.compile(
    r"\b(?:(?<!não\s)podem?\s+ter\s+[a-zà-ú]+(?:ado|ada|ido|ida|ído|to|so|cho)\b"
    r"|poderia|poderiam|teria\s+sido|teriam\s+sido|talvez|possivelmente|provavelmente"
    r"|supostamente|alegadamente|aparentemente|estima-se|projeta-se|prevê-se|espera-se"
    r"|segundo\s+(?:as\s+)?(?:projeções|estimativas|rumores)|deve\s+atingir"
    r"|rumores?|boatos?|especula-se|especulaç(?:ão|ões)"
    r"|não\s+se\s+sabe\s+se|ninguém\s+sabe\s+se|é\s+incerto\s+se|não\s+está\s+claro\s+se"
    r"|não\s+há\s+confirmação\s+de\s+que|sem\s+confirmação"
    r"|may\s+have|might|could\s+have|reportedly|allegedly|expected\s+to|rumou?rs?"
    r"|unclear\s+whether|not\s+known\s+whether)\b"
    r"|\bse\b[^.;!?]{0,200}?\b(?:fosse|fossem|tivesse|tivessem)\b",
    re.IGNORECASE,
)


# A sentence that opens with a condition states the claim only as a hypothesis.
_CONDITIONAL_OPENING_RE = re.compile(
    r"^\W*(?:se|caso|supondo\s+que|assumindo\s+que|na\s+hipótese\s+de|if|unless"
    r"|assuming|suppose|supposing)\b",
    re.IGNORECASE,
)
# Goal, plan or intention words: the sentence states a target, not a fact. Ignored
# when the word is part of the claim itself ("a meta de inflação foi de 3%").
_GOAL_WORDS = frozenset(
    {
        "meta",
        "metas",
        "objetivo",
        "objetivos",
        "pretende",
        "pretendem",
        "planeja",
        "planejam",
        "visa",
        "visam",
        "almeja",
        "almejam",
        "target",
        "targets",
        "goal",
        "goals",
        "aims",
        "plans",
        "intends",
    }
)
# A correction notice neutralizes only the claim sentence it immediately qualifies:
# same sentence, the preceding sentence (a trailing errata notice), or the following
# sentence (a leading standalone "Errata."). A distant notice must not contaminate
# an unrelated assertion elsewhere in a multi-claim document.
_CORRECTION_RE = re.compile(
    r"\b(?:retificação|retificacao|errata|erratum|correção|correcao|correction|corrigido"
    r"|corrected|o\s+(?:valor|número|dado)\s+correto|the\s+correct\s+(?:figure|value))\b",
    re.IGNORECASE,
)


def _non_assertive(text: str, claim_tokens: frozenset[str]) -> bool:
    """A claim sentence is non-assertive, or a nearby correction notice qualifies it."""
    paragraphs = [part for part in re.split(r"\n\s*\n", text.strip()) if part]
    correction_notices_apply = not _CORRECTION_RE.search(" ".join(claim_tokens))
    for paragraph in paragraphs:
        sentences = [sentence for sentence in _SENTENCE_SPLIT_RE.split(paragraph) if sentence]
        for index, sentence in enumerate(sentences):
            if not _covers_claim(sentence, claim_tokens):
                continue
            if correction_notices_apply and _CORRECTION_RE.search(sentence):
                return True
            if (
                correction_notices_apply
                and index > 0
                and _CORRECTION_RE.search(sentences[index - 1])
            ):
                return True
            if (
                correction_notices_apply
                and index + 1 < len(sentences)
                and _CORRECTION_RE.search(sentences[index + 1])
            ):
                return True
            if _NON_ASSERTIVE_RE.search(sentence):
                return True
            if sentence.rstrip().endswith("?") or _CONDITIONAL_OPENING_RE.search(sentence):
                return True
            words = {token.casefold() for token in _TOKEN_RE.findall(sentence)}
            if (words & _GOAL_WORDS) - claim_tokens:
                return True
    return False


def _reported_denial(text: str, claim_tokens: frozenset[str]) -> bool:
    """The text reports that someone denied a proposition covering the claim."""
    return any(
        _covers_claim(_clause_after(text, match.end()), claim_tokens)
        for match in _REPORTED_DENIAL_RE.finditer(text)
    )


def _clause_after(text: str, start: int) -> str:
    """Text from ``start`` to the end of its clause."""
    end = _CLAUSE_END_RE.search(text, start)
    return text[start : end.start() if end else len(text)]


def _covers_claim(scope: str, claim_tokens: frozenset[str]) -> bool:
    """The scope holds at least half of the claim's content tokens."""
    if not claim_tokens:
        return True
    tokens = {token.casefold() for token in _TOKEN_RE.findall(scope)}
    return len(claim_tokens & tokens) / len(claim_tokens) >= _OPERATOR_SCOPE_COVERAGE


def _has_token_negation(text: str) -> bool:
    tokens = {token.casefold() for token in _TOKEN_RE.findall(text)}
    if _predicate_negators(text) & _NEGATION_TOKENS_PT:
        return True
    pt, en = _language_scores(text)
    pt += len(tokens & _PT_FUNCTION_WORDS)
    # "no" is an English negator only in a sentence that shows English: with no
    # marker on either side ("A Holding Rios investe no setor têxtil.") it is the
    # Portuguese contraction "em + o".
    if en > pt or (en == pt and en > 0):
        return bool(tokens & _NEGATION_TOKENS_EN)
    return bool(tokens & (_NEGATION_TOKENS_EN - {"no"}))


# "não superior a", "não pode ser superior", "não excede", "nem superior": a
# bound on a quantity, not a negated predicate.
_COMPARATIVES = frozenset(
    {
        "superior",
        "superiores",
        "inferior",
        "inferiores",
        "excede",
        "exceder",
        "exceda",
        "excedam",
        "ultrapassa",
        "ultrapassar",
        "ultrapasse",
        "maior",
        "maiores",
        "menor",
        "menores",
        "mais",
        "menos",
    }
)
_FUNCTION_WORDS = frozenset(
    {
        "das",
        "dos",
        "para",
        "com",
        "que",
        "pela",
        "pelo",
        "pelos",
        "pelas",
        "uma",
        "por",
        "entre",
        "sobre",
        "até",
        "ate",
        "sem",
        "mais",
        "menos",
        "seu",
        "sua",
        "seus",
        "suas",
        "ser",
        "ter",
        "foi",
        "são",
        "sao",
        "não",
        "nao",
        "quando",
        "como",
        "este",
        "esta",
        "esse",
        "essa",
        "nos",
        "nas",
        "aos",
        "the",
        "and",
        "for",
        "with",
        "was",
        "were",
        "from",
        "that",
        "this",
    }
)


def _content_words(text: str) -> set[str]:
    """Content words: numbers, number words, units and function words excluded."""
    return {
        word
        for word in (strip_accents(t.casefold()) for t in _TOKEN_RE.findall(text))
        if len(word) > 2
        and not word.isdigit()
        and word not in _STOPWORDS
        and word not in _FUNCTION_WORDS
        and word not in _DURATION_WORDS
        and word not in _MEASURE_WORDS
        and normalize_numerals(word) == word
    }


def _content_overlap(claim_text: str, evidence_text: str) -> float:
    """Share of claim content words found in the evidence.

    Numbers, number words, units and function words are excluded, so a shared
    quantity ("seis meses") does not count as a shared subject.
    """
    claim_words = _content_words(claim_text)
    if not claim_words:
        return 0.0
    return len(claim_words & _content_words(evidence_text)) / len(claim_words)


_SENTENCE_ENDS = frozenset({".", "!", "?"})


def _proper_nouns(text: str) -> set[str]:
    """Capitalized words that do not open a sentence (names such as "Vértice")."""
    names: set[str] = set()
    sentence_start = True
    for match in re.finditer(r"[\wÀ-ÿ]+|[.!?]", text):
        word = match.group(0)
        if word in _SENTENCE_ENDS:
            sentence_start = True
            continue
        if word[:1].isupper() and not sentence_start:
            names.add(strip_accents(word.casefold()))
        sentence_start = False
    return names


# Auxiliary and possession verbs: shared, they say nothing about which event
# two sentences describe ("tem sede" and "tem 40 lojas").
_GENERIC_VERBS = frozenset(
    """
    ter tem tens temos teem tinha tinham teve tiveram tera teria possui possuem possuia
    possuiam ser foi foram era eram sao sera seria estar esta estao estava estavam
    ficou ficaram haver houve havia
    """.split()
)


def _shares_predicate(claim_text: str, evidence_text: str) -> bool:
    """Claim and evidence share a content word that is neither a name nor a generic verb.

    The subject's name alone ("Vértice") does not make two sentences talk about
    the same event; a shared predicate word ("fundada", "receita") does. A name is
    recognized when it is capitalized inside a sentence in either text, so a name
    that opens the claim ("Vértice foi fundada…") is still a name.
    """
    names = (
        _proper_nouns(claim_text)
        | _proper_nouns(evidence_text)
        | _initial_names(claim_text, evidence_text)
    )
    heads = _name_heads(claim_text) | _name_heads(evidence_text)
    claim_words = _content_words(claim_text) - names - heads - _GENERIC_VERBS
    return bool(claim_words & _content_words(evidence_text))


# Common nouns that only name the kind of a named entity when they stand right
# before its name: "o município de Serra Alta", "o estudo Coorte Aurora". In that
# position they belong to the subject, not to the predicate.
_ENTITY_TYPE_NOUNS = frozenset(
    {
        "municipio",
        "cidade",
        "estado",
        "regiao",
        "pais",
        "distrito",
        "bairro",
        "estudo",
        "sistema",
        "programa",
        "projeto",
        "city",
        "state",
        "region",
        "country",
        "study",
        "system",
        "program",
        "project",
    }
)
_NAME_HEAD_RE = re.compile(r"\b([a-zà-ÿ]+)\s+(?:(?:de|do|da|dos|das|of)\s+)?[A-ZÀ-Ý][\wÀ-ÿ]*")


def _name_heads(text: str) -> set[str]:
    """Entity-type nouns standing right before a capitalized name."""
    return {
        word
        for word in (strip_accents(m.group(1).casefold()) for m in _NAME_HEAD_RE.finditer(text))
        if word in _ENTITY_TYPE_NOUNS
    }


def _initial_names(claim_text: str, evidence_text: str) -> set[str]:
    """Capitalized words that open a sentence and never appear in lowercase.

    "Vértice foi fundada em 1998." against "Vértice abriu filial em 2001." names
    Vértice only at the start of both sentences, so ``_proper_nouns`` cannot tell it
    from a common word. A word written in lowercase anywhere in either text
    ("Fundada em 1998, …" next to "foi fundada") is a common word and stays a
    possible predicate; one that is only ever capitalized is treated as a name, so
    it cannot anchor a year conflict on its own. When the doubt remains, the year
    is not anchored and the passage abstains instead of refuting.
    """
    initials: set[str] = set()
    lowercase: set[str] = set()
    for text in (claim_text, evidence_text):
        sentence_start = True
        for match in re.finditer(r"[\wÀ-ÿ]+|[.!?]", text):
            word = match.group(0)
            if word in _SENTENCE_ENDS:
                sentence_start = True
                continue
            folded = strip_accents(word.casefold())
            if sentence_start and word[:1].isupper():
                initials.add(folded)
            elif word[:1].islower():
                lowercase.add(folded)
            sentence_start = False
    return initials - lowercase


def _predicate_negators(text: str) -> set[str]:
    """Negator tokens that negate a predicate (comparative bounds excluded)."""
    tokens = [token.casefold() for token in _TOKEN_RE.findall(text)]
    found: set[str] = set()
    for index, token in enumerate(tokens):
        if token not in _NEGATION_TOKENS_PT:
            continue
        window = tokens[index + 1 : index + 5]
        if any(word in _COMPARATIVES for word in window):
            continue
        found.add(token)
    return found


def _competing_entity(claim_text: str, evidence_text: str) -> bool:
    """The evidence names actors and none of the claim's named actors is among them."""
    claim_names = named_entities(claim_text)
    evidence_names = named_entities(evidence_text)
    if not claim_names or not evidence_names:
        return False
    evidence_words = set(_TOKEN_RE.findall(strip_accents(evidence_text.casefold())))

    def present(name: str) -> bool:
        distinctive = [
            word
            for word in name.split()
            if word not in GENERIC_NAME_WORDS and word not in {"de", "do", "da", "dos", "das", "e"}
        ]
        return bool(distinctive) and all(word in evidence_words for word in distinctive)

    return not any(present(name) for name in claim_names)


# Nouns that name a part of an organization or place. "o lucro da agência de
# Belém do Banco Horizonte" reports the branch, not the bank.
_SUBUNIT_WORDS = frozenset(
    {
        "filial",
        "filiais",
        "agencia",
        "agencias",
        "unidade",
        "unidades",
        "posto",
        "sucursal",
        "subsidiaria",
        "campus",
        "anexo",
        "loja",
        "armazem",
        "terminal",
        "ramal",
        "distrito",
        "subprefeitura",
        "diretoria",
        "nucleo",
        "modulo",
        "bloco",
        "braco",
        "subestudo",
        "escritorio",
        "fabrica",
        "planta",
        "branch",
        "subsidiary",
        "division",
        "divisao",
    }
)
_SUBUNIT_WINDOW = 8


_SUBUNIT_PHRASE_BREAKS = frozenset({"o", "a", "os", "as", "the"})


def _subunit_before(prefix: str, claim_words: set[str]) -> bool:
    """A subunit noun heads the noun phrase that ends with the claim's name.

    "agência de Belém do Banco Horizonte" qualifies; in "com 300 agências, o lucro
    do Banco Horizonte" the comma and the article open another phrase.
    """
    clause = re.split(r"[,;:.!?()]", prefix)[-1]
    words = _TOKEN_RE.findall(clause)[-_SUBUNIT_WINDOW:]
    for index, word in enumerate(words):
        if word in _SUBUNIT_WORDS and word not in claim_words:
            if not _SUBUNIT_PHRASE_BREAKS.intersection(words[index + 1 :]):
                return True
    return False


def _entity_variant(claim_text: str, evidence_text: str) -> bool:
    """The passage names a part or a longer-named sibling of the claim's entity.

    For each multi-word name of the claim found in the passage: a longer name that
    starts with it ("Banco Horizonte Sul" for "Banco Horizonte"), or a subunit noun
    just before it that the claim does not use ("posto de Lages da Cooperativa
    Serra Azul"), means the passage reports another entity.
    """
    claim_folded = strip_accents(claim_text.casefold())
    claim_words = set(_TOKEN_RE.findall(claim_folded))
    evidence_folded = strip_accents(evidence_text.casefold())
    evidence_names = named_entities(evidence_text)
    for name in named_entities(claim_text):
        position = evidence_folded.find(name)
        if position < 0:
            continue
        for other in evidence_names:
            if not other.startswith(name + " ") or other in claim_folded:
                continue
            extra = other[len(name) :].split()
            if any(
                word not in GENERIC_NAME_WORDS and word not in {"de", "do", "da", "dos", "das", "e"}
                for word in extra
            ):
                return True
        if _subunit_before(evidence_folded[:position], claim_words):
            return True
    return False


def _directions(text: str) -> dict[str, set[int]]:
    """Return the directional polarities asserted per axis."""
    found: dict[str, set[int]] = {}
    for token in _TOKEN_RE.findall(text):
        term = _DIRECTION_TERMS.get(token.casefold())
        if term is not None:
            found.setdefault(term[0], set()).add(term[1])
    return found


def _direction_conflict(claim_text: str, evidence_text: str) -> bool:
    """Opposite direction on a shared axis, with no same-direction support.

    Negated text is excluded: polarity reasoning under negation is left to the
    negation rule, so "não caiu" is never treated as "subiu".
    """
    if _has_negation(claim_text) or _has_negation(evidence_text):
        return False
    claim_directions = _directions(claim_text)
    evidence_directions = _directions(evidence_text)
    for axis, claim_polarities in claim_directions.items():
        evidence_polarities = evidence_directions.get(axis)
        if not evidence_polarities or len(claim_polarities) != 1:
            continue
        if not claim_polarities & evidence_polarities:
            return True
    return False


DateKey = tuple[str, int, int, int]


def _slash_date(first: int, second: int, year: int, language: str) -> DateKey | None:
    day, month = (first, second) if language == "pt" else (second, first)
    try:
        date(year, month, day)
    except ValueError:
        return None
    return ("day", year, month, day)


def _extract_dates(text: str) -> set[DateKey]:
    """Extract dates with the granularity the text asserts.

    Supports ISO `2026-03-10`, `10 de março de 2026`, `1º de abril de 2026`,
    `10/03/2026` (day/month in Portuguese, month/day in English) and
    `março de 2026` (month granularity). Invalid calendar dates are ignored.
    """
    found: set[DateKey] = set()
    for match in _DATE_RE.finditer(text):
        try:
            parsed = date.fromisoformat(match.group(0))
        except ValueError:
            continue
        found.add(("day", parsed.year, parsed.month, parsed.day))
    day_spans: list[tuple[int, int]] = []
    for match in _PT_DAY_DATE_RE.finditer(text):
        year = int(match.group("year"))
        month = _PT_MONTHS[match.group("month").casefold()]
        day = int(match.group("day"))
        day_spans.append(match.span())
        try:
            date(year, month, day)
        except ValueError:
            continue
        found.add(("day", year, month, day))
    for match in _PT_MONTH_DATE_RE.finditer(text):
        start = match.start()
        if any(left <= start < right for left, right in day_spans):
            continue
        month = _PT_MONTHS[match.group("month").casefold()]
        found.add(("month", int(match.group("year")), month, 0))
    language = detect_language(text)
    for match in _SLASH_DATE_RE.finditer(text):
        key = _slash_date(
            int(match.group("a")), int(match.group("b")), int(match.group("year")), language
        )
        if key is not None:
            found.add(key)
    return found


def _same_date(left: DateKey, right: DateKey) -> bool:
    """Compare at the coarser of the two asserted granularities."""
    if left[0] == "month" or right[0] == "month":
        return left[1:3] == right[1:3]
    return left == right


def _dates_conflict(claim_text: str, evidence_text: str) -> bool:
    claim_dates = _extract_dates(claim_text)
    evidence_dates = _extract_dates(evidence_text)
    if not claim_dates or not evidence_dates:
        return False
    return not any(_same_date(left, right) for left in claim_dates for right in evidence_dates)


def _strip_dates(text: str) -> str:
    for pattern in (_DATE_RE, _PT_DAY_DATE_RE, _PT_MONTH_DATE_RE, _SLASH_DATE_RE):
        text = pattern.sub(" ", text)
    return text


_FACT_TOKEN_RE = re.compile(
    r"(?<![\w-])[-+]?\d+(?:[.,]\d+)*(?:\s*%)?|[\wÀ-ÿ]+",
    re.UNICODE,
)
# Currency symbols are rewritten to ISO codes before tokenization so that
# "R$ 10", "US$ 10", "$10" and "10 USD" share one representation.
_CURRENCY_SYMBOLS = (
    (re.compile(r"R\$"), " brl "),
    (re.compile(r"US\$"), " usd "),
    (re.compile(r"\$"), " usd "),
    (re.compile(r"€"), " eur "),
)
_CURRENCIES = frozenset({"usd", "eur", "brl"})
_SCALES: dict[str, tuple[str, Decimal]] = {
    "thousand": ("thousand", Decimal(10) ** 3),
    "mil": ("thousand", Decimal(10) ** 3),
    "million": ("million", Decimal(10) ** 6),
    "millions": ("million", Decimal(10) ** 6),
    "milhão": ("million", Decimal(10) ** 6),
    "milhao": ("million", Decimal(10) ** 6),
    "milhões": ("million", Decimal(10) ** 6),
    "milhoes": ("million", Decimal(10) ** 6),
    "billion": ("billion", Decimal(10) ** 9),
    "billions": ("billion", Decimal(10) ** 9),
    "bilhão": ("billion", Decimal(10) ** 9),
    "bilhao": ("billion", Decimal(10) ** 9),
    "bilhões": ("billion", Decimal(10) ** 9),
    "bilhoes": ("billion", Decimal(10) ** 9),
}
_SCALE_FACTORS = {"base": Decimal(1), **{name: factor for name, factor in _SCALES.values()}}
_CONNECTORS = frozenset({"de", "of", "em", "in"})
_MILLISECOND_WORDS = frozenset(
    {"ms", "millisecond", "milliseconds", "milissegundo", "milissegundos"}
)
_PERCENT_WORDS = frozenset({"percent", "porcento", "pct"})
_COUNT_NOUNS: dict[str, str] = {
    "employees": "employees",
    "funcionários": "employees",
    "funcionarios": "employees",
    "colaboradores": "employees",
    "people": "people",
    "pessoas": "people",
    "customers": "customers",
    "clientes": "customers",
    "offices": "offices",
    "escritórios": "offices",
    "escritorios": "offices",
}
_ATTRIBUTE_ALIASES = {
    "receita": "revenue",
    "faturamento": "revenue",
    "revenue": "revenue",
    "lucro": "profit",
    "profit": "profit",
    "custo": "cost",
    "custos": "cost",
    "cost": "cost",
    "costs": "cost",
    "margem": "margin",
    "margin": "margin",
}
# Durations share one scale per family so "1 ano" and "12 meses" compare.
_DURATION_WORDS: dict[str, tuple[str, Decimal]] = {
    "ano": ("months", Decimal(12)),
    "anos": ("months", Decimal(12)),
    "year": ("months", Decimal(12)),
    "years": ("months", Decimal(12)),
    "mês": ("months", Decimal(1)),
    "mes": ("months", Decimal(1)),
    "meses": ("months", Decimal(1)),
    "month": ("months", Decimal(1)),
    "months": ("months", Decimal(1)),
    "dia": ("hours", Decimal(24)),
    "dias": ("hours", Decimal(24)),
    "day": ("hours", Decimal(24)),
    "days": ("hours", Decimal(24)),
    "hora": ("hours", Decimal(1)),
    "horas": ("hours", Decimal(1)),
    "hour": ("hours", Decimal(1)),
    "hours": ("hours", Decimal(1)),
}
# Physical units share the duration machinery: a family (the dimension) and a
# factor to its base unit, so "120 MW" and "120.000 kW" are the same quantity and
# "120 MW" against "120 kW" is a conflict, never a match of the bare number 120.
# Ambiguous words are left out: "segundo" is also "according to", "second" an
# ordinal, and a bare "g" too short to be safe.
_PHYSICAL_UNITS: dict[str, tuple[str, Decimal]] = {
    "w": ("power", Decimal(1)),
    "watt": ("power", Decimal(1)),
    "watts": ("power", Decimal(1)),
    "kw": ("power", Decimal(10) ** 3),
    "quilowatt": ("power", Decimal(10) ** 3),
    "quilowatts": ("power", Decimal(10) ** 3),
    "kilowatt": ("power", Decimal(10) ** 3),
    "kilowatts": ("power", Decimal(10) ** 3),
    "mw": ("power", Decimal(10) ** 6),
    "megawatt": ("power", Decimal(10) ** 6),
    "megawatts": ("power", Decimal(10) ** 6),
    "gw": ("power", Decimal(10) ** 9),
    "gigawatt": ("power", Decimal(10) ** 9),
    "gigawatts": ("power", Decimal(10) ** 9),
    "kwh": ("energy", Decimal(10) ** 3),
    "mwh": ("energy", Decimal(10) ** 6),
    "gwh": ("energy", Decimal(10) ** 9),
    "twh": ("energy", Decimal(10) ** 12),
    "m": ("length", Decimal(1)),
    "metro": ("length", Decimal(1)),
    "metros": ("length", Decimal(1)),
    "meter": ("length", Decimal(1)),
    "meters": ("length", Decimal(1)),
    "km": ("length", Decimal(10) ** 3),
    "quilômetro": ("length", Decimal(10) ** 3),
    "quilômetros": ("length", Decimal(10) ** 3),
    "quilometro": ("length", Decimal(10) ** 3),
    "quilometros": ("length", Decimal(10) ** 3),
    "kilometer": ("length", Decimal(10) ** 3),
    "kilometers": ("length", Decimal(10) ** 3),
    "grama": ("mass", Decimal(1)),
    "gramas": ("mass", Decimal(1)),
    "kg": ("mass", Decimal(10) ** 3),
    "quilo": ("mass", Decimal(10) ** 3),
    "quilos": ("mass", Decimal(10) ** 3),
    "quilograma": ("mass", Decimal(10) ** 3),
    "quilogramas": ("mass", Decimal(10) ** 3),
    "tonelada": ("mass", Decimal(10) ** 6),
    "toneladas": ("mass", Decimal(10) ** 6),
    "ton": ("mass", Decimal(10) ** 6),
    "tons": ("mass", Decimal(10) ** 6),
    "segundos": ("seconds", Decimal(1)),
    "seconds": ("seconds", Decimal(1)),
    "minuto": ("seconds", Decimal(60)),
    "minutos": ("seconds", Decimal(60)),
    "minute": ("seconds", Decimal(60)),
    "minutes": ("seconds", Decimal(60)),
}
_MEASURE_WORDS = {
    "vez": "times",
    "vezes": "times",
    "times": "times",
    "diasmulta": "day_fines",
    "diamulta": "day_fines",
}
_DAY_FINE_RE = re.compile(r"\bdias?-multa\b", re.IGNORECASE)
_EXACT_UNITS = frozenset({"year", "fraction", "multiplier"})
_YEAR_MIN = 1900
_YEAR_MAX = 2100


def _fact_tokens(text: str) -> list[str]:
    normalized = _strip_dates(text)
    for pattern, replacement in _CURRENCY_SYMBOLS:
        normalized = pattern.sub(replacement, normalized)
    return _FACT_TOKEN_RE.findall(normalized.casefold())


def _is_number(token: str) -> bool:
    return any(character.isdigit() for character in token)


def _currency_and_scale(tokens: list[str], index: int) -> tuple[str, str] | None:
    """Return (currency, scale) only when a currency is bound to this number.

    Accepted shapes: `USD 120 [million]` and `120 [million] [de|of] USD`.
    A currency elsewhere in the sentence never binds, so years and counts
    near a monetary value are not misread as money.
    """
    scale = "base"
    cursor = index + 1
    if cursor < len(tokens) and tokens[cursor] in _SCALES:
        scale = _SCALES[tokens[cursor]][0]
        cursor += 1
    if index > 0 and tokens[index - 1] in _CURRENCIES:
        return tokens[index - 1], scale
    if cursor < len(tokens) and tokens[cursor] in _CONNECTORS:
        cursor += 1
    if cursor < len(tokens) and tokens[cursor] in _CURRENCIES:
        return tokens[cursor], scale
    return None


def _attribute(tokens: list[str], index: int, entities: set[str]) -> str:
    """Nearest attribute alias in the clause, else nearest content word before."""
    for distance in range(1, 9):
        for position in (index - distance, index + distance):
            if 0 <= position < len(tokens) and tokens[position] in _ATTRIBUTE_ALIASES:
                return _ATTRIBUTE_ALIASES[tokens[position]]
    for position in range(index - 1, max(-1, index - 5), -1):
        value = tokens[position]
        if (
            not _is_number(value)
            and value not in _STOPWORDS
            and value not in _UNIT_WORDS
            and value not in _CURRENCIES
            and value not in _SCALES
            and value not in _CONNECTORS
            and value not in entities
        ):
            return value
    return "unknown"


# A number introduced by a bound ("superou 40", "abaixo de 40", "mais de 40",
# "at least 40") states an inequality, not a value: on the evidence side it can
# neither confirm nor contradict an exact claimed value. When the claim is itself
# a bound ("pode chegar a dez vezes", "até trinta anos") bounds compare as before.
# Calendar years are never treated as bounded values.
_BOUND_WORDS = frozenset(
    {
        "superou",
        "superar",
        "supera",
        "ultrapassou",
        "ultrapassar",
        "ultrapassa",
        "excedeu",
        "exceder",
        "excede",
        "acima",
        "abaixo",
        "mais",
        "menos",
        "inferior",
        "superior",
        "mínimo",
        "minimo",
        "máximo",
        "maximo",
        "over",
        "above",
        "below",
        "under",
        "exceeded",
        "exceeds",
        "surpassed",
        "more",
        "less",
        "fewer",
        "least",
        "most",
        "até",
        "ate",
        "chegar",
        "up",
    }
)
_BOUND_FILLERS = frozenset({"de", "a", "do", "da", "o", "than", "of", "at", "pelo", "no"})


def _is_bound(tokens: list[str], index: int) -> bool:
    """The number at ``index`` is introduced by a bound word (skipping fillers)."""
    position = index - 1
    while position >= 0 and index - position <= 3 and tokens[position] in _BOUND_FILLERS:
        position -= 1
    return position >= 0 and index - position <= 3 and tokens[position] in _BOUND_WORDS


_HISTORICAL_YEAR_MIN = 1000
_TEMPORAL_PREPOSITIONS = frozenset({"em", "desde", "in", "since"})


def _is_historical_year(tokens: list[str], index: int) -> bool:
    """A four-digit year before 1900, introduced by a temporal preposition.

    "fundada em 1745" and "no ano de 1872" are calendar years and compare
    exactly; a bare "1745" may be a quantity, so it stays a scalar.
    """
    token = tokens[index]
    if not (token.isdigit() and len(token) == 4):
        return False
    if not _HISTORICAL_YEAR_MIN <= int(token) < _YEAR_MIN:
        return False
    before = tokens[index - 1] if index >= 1 else ""
    if before in _TEMPORAL_PREPOSITIONS:
        return True
    return before in {"de", "of"} and index >= 2 and tokens[index - 2] in {"ano", "year"}


def _is_year_token(token: str) -> bool:
    return token.isdigit() and len(token) == 4 and _YEAR_MIN <= int(token) <= _YEAR_MAX


def _has_bound(text: str) -> bool:
    """Some non-year number in the text is introduced by a bound word."""
    tokens = _fact_tokens(normalize_numerals(text))
    return any(
        _is_number(token) and not _is_year_token(token) and _is_bound(tokens, index)
        for index, token in enumerate(tokens)
    )


_EN_MONTHS = frozenset(
    {
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    }
)
_NAME_SCAN_RE = re.compile(r"\d+(?:[.,]\d+)*|[A-Za-zÀ-ÿ]+|[.!?%]")
_TITLE_WORD_RE = re.compile(r"[A-ZÀ-Ý][a-zà-ÿ]+")


def _number_word_value(word: str) -> str | None:
    """Digits of a single Portuguese number word ("Três" -> "3"), else None."""
    value = normalize_numerals(word.casefold())
    return value if value.isdigit() else None


def _mask_name_numerals(text: str) -> tuple[str, list[str]]:
    """Blank out numerals that belong to a proper name and return their values.

    A name is a run of capitalized words. A capitalized number word belongs to it
    when the next word is a capitalized word ("Três Rios") or the previous one is
    a capitalized word that does not open the sentence ("Holding Três"). Digits
    belong to it when they follow such a word ("Construtora 2000") and are not
    followed by a percent, scale, currency or unit ("Vértice 40 milhões").
    Capitalized means an initial capital followed by lowercase letters, so codes
    (USD, MW, Q3) do not form names; month names do not either ("March 2024").
    """
    tokens = list(_NAME_SCAN_RE.finditer(text))
    sentence_start = [True] * len(tokens)
    for index in range(1, len(tokens)):
        sentence_start[index] = tokens[index - 1].group(0) in {".", "!", "?"}

    def adjacent(left: int, right: int) -> bool:
        return (
            0 <= left
            and right < len(tokens)
            and (text[tokens[left].end() : tokens[right].start()].isspace())
        )

    def name_word(index: int) -> bool:
        if not 0 <= index < len(tokens):
            return False
        word = tokens[index].group(0)
        folded = word.casefold()
        return (
            _TITLE_WORD_RE.fullmatch(word) is not None
            and _number_word_value(word) is None
            and folded not in _PT_MONTHS
            and folded not in _EN_MONTHS
        )

    def quantity_after(index: int) -> bool:
        if index + 1 >= len(tokens):
            return False
        following = tokens[index + 1].group(0).casefold()
        return (
            following == "%"
            or following in _PERCENT_WORDS
            or following in _SCALES
            or following in _CURRENCIES
            or following in _MILLISECOND_WORDS
            or following in _COUNT_NOUNS
            or following in _DURATION_WORDS
            or following in _PHYSICAL_UNITS
            or following in _MEASURE_WORDS
            or following in _UNIT_WORDS
            or following == "por"
        )

    def named_before(index: int) -> bool:
        return name_word(index - 1) and not sentence_start[index - 1] and adjacent(index - 1, index)

    values: list[str] = []
    spans: list[tuple[int, int]] = []
    for index, match in enumerate(tokens):
        token = match.group(0)
        if token[:1].isdigit():
            is_name = named_before(index) and not quantity_after(index)
            value = token.replace(".", "").replace(",", "")
        else:
            number = _number_word_value(token) if _TITLE_WORD_RE.fullmatch(token) else None
            is_name = number is not None and (
                (name_word(index + 1) and adjacent(index, index + 1)) or named_before(index)
            )
            value = number or ""
        if is_name:
            values.append(value)
            spans.append(match.span())
    if not spans:
        return text, values
    pieces: list[str] = []
    cursor = 0
    for start, end in spans:
        pieces.append(text[cursor:start])
        pieces.append(" " * (end - start))
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces), values


def _numeric_facts(text: str, *, skip_bounds: bool = False) -> list[tuple[str, str, str]]:
    """Extract (raw value, unit, attribute) facts deterministically.

    `unit` is `currency:scale` for money, `percent`, `year`, `ms`,
    `count:<noun>`, `scalar`, or `name` for a numeral that belongs to a proper
    name ("Holding Três Rios", "Construtora 2000"). Extraction never raises on
    free text.
    """
    text, name_values = _mask_name_numerals(text)
    quantity_facts, remaining = extract_quantities(_DAY_FINE_RE.sub(" diasmulta ", text))
    tokens = _fact_tokens(normalize_numerals(remaining))
    entities = _entities(text)
    facts: list[tuple[str, str, str]] = [(value, "name", "name") for value in name_values]
    facts.extend(quantity_facts)
    for index, token in enumerate(tokens):
        if not _is_number(token):
            continue
        if skip_bounds and not _is_year_token(token) and _is_bound(tokens, index):
            continue
        following = tokens[index + 1] if index + 1 < len(tokens) else ""
        money = _currency_and_scale(tokens, index)
        if (
            "%" in token
            or following in _PERCENT_WORDS
            or (following == "por" and index + 2 < len(tokens) and tokens[index + 2] == "cento")
        ):
            unit = "percent"
        elif money is not None:
            unit = f"{money[0]}:{money[1]}"
        elif following in _SCALES:
            # "1,2 bilhão" and "1.200 milhões" without a currency: the scale is
            # part of the value, so both compare as the same quantity. A count
            # noun shortly after ("2,0 milhões de clientes", "2.0 million active
            # retail customers") makes it a scaled count of that noun.
            scale = _SCALES[following][0]
            noun = _scaled_count_noun(tokens, index + 2)
            unit = f"count:{noun}:{scale}" if noun else f"scaled:{scale}"
        elif following in _MILLISECOND_WORDS:
            # Milliseconds are time: "50 ms" and "0,05 segundos" are the same quantity.
            unit = "ms"
        elif following in _COUNT_NOUNS:
            unit = f"count:{_COUNT_NOUNS[following]}"
        elif following in _DURATION_WORDS:
            family, factor = _DURATION_WORDS[following]
            unit = f"duration:{family}:{factor}"
        elif following in _PHYSICAL_UNITS:
            family, factor = _PHYSICAL_UNITS[following]
            unit = f"duration:{family}:{factor}"
        elif following in _MEASURE_WORDS:
            unit = f"measure:{_MEASURE_WORDS[following]}"
        elif token.isdigit() and len(token) == 4 and _YEAR_MIN <= int(token) <= _YEAR_MAX:
            unit = "year"
        elif _is_historical_year(tokens, index):
            unit = "year"
        else:
            unit = "scalar"
        if unit == "year":
            attribute = "year"
        elif unit.startswith("duration:"):
            attribute = unit.rsplit(":", 1)[0]
        elif unit.startswith(("count:", "measure:")):
            attribute = ":".join(unit.split(":")[:2])
        else:
            attribute = _attribute(tokens, index, entities)
        facts.append((token.replace(" ", ""), unit, attribute))
    return facts


_SCALED_COUNT_WINDOW = 3


def _scaled_count_noun(tokens: list[str], start: int) -> str | None:
    """Count noun within a few words after a scale word, before any number."""
    for position in range(start, min(len(tokens), start + _SCALED_COUNT_WINDOW)):
        token = tokens[position]
        if _is_number(token):
            return None
        if token in _COUNT_NOUNS:
            return _COUNT_NOUNS[token]
    return None


def _locale_for(text: str) -> NumericLocale:
    return NumericLocale.PT_BR if detect_language(text) == "pt" else NumericLocale.EN_US


def _fact_value(
    raw: str, unit: str, locale: NumericLocale, *, as_written: bool = False
) -> Decimal | None:
    """Numeric value of a fact; durations are scaled to their family unless as_written."""
    if unit in {"fraction", "multiplier"}:
        numerator, _, denominator = raw.partition("/")
        return Decimal(numerator) / Decimal(denominator or "1")
    try:
        value = parse_number(raw, locale=locale)
    except (ValueError, ArithmeticError):
        return None
    if unit.startswith("duration:"):
        return value if as_written else value * Decimal(unit.rsplit(":", 1)[1])
    if unit.startswith("measure:"):
        return value
    if unit.startswith("count:"):
        parts = unit.split(":")
        if len(parts) == 3:
            value *= _SCALE_FACTORS[parts[2]]
    elif ":" in unit:
        value *= _SCALE_FACTORS.get(unit.split(":", 1)[1], Decimal(1))
    return value


def _comparable(left_unit: str, right_unit: str) -> bool:
    if left_unit == right_unit:
        return True
    if left_unit.startswith("scaled:") and right_unit.startswith("scaled:"):
        return True
    if left_unit.startswith("count:") and right_unit.startswith("count:"):
        return left_unit.split(":")[1] == right_unit.split(":")[1]
    if left_unit.startswith("duration:") and right_unit.startswith("duration:"):
        return left_unit.rsplit(":", 1)[0] == right_unit.rsplit(":", 1)[0]
    left_money = left_unit.split(":", 1)[0] in _CURRENCIES
    right_money = right_unit.split(":", 1)[0] in _CURRENCIES
    return left_money and right_money and left_unit.split(":")[0] == right_unit.split(":")[0]


def _numeric_relation(claim_text: str, evidence_text: str) -> tuple[bool, bool]:
    conflict, agreement, _ = _numeric_facts_align(claim_text, evidence_text)
    return conflict, agreement


def _entities(text: str) -> set[str]:
    return {match.group("name").casefold() for match in _ENTITY_RE.finditer(text)}


@dataclass(frozen=True)
class NumericAlignment:
    """Outcome of comparing claim facts with evidence facts.

    `generic_*` flags come from units whose attribute is the unit itself
    (durations, measures, fractions, multipliers). They carry no subject, so the
    detector only trusts them when claim and evidence share the proposition.
    """

    specific_conflict: bool = False
    generic_conflict: bool = False
    specific_agreement: bool = False
    generic_agreement: bool = False
    all_matched: bool = True

    @property
    def conflict(self) -> bool:
        return self.specific_conflict or self.generic_conflict

    @property
    def agreement(self) -> bool:
        return self.specific_agreement or self.generic_agreement


def _is_generic(unit: str) -> bool:
    return unit.startswith(("duration:", "measure:")) or unit in {"fraction", "multiplier"}


def _mask_comparison_baselines(text: str, claim_years: frozenset[str] = frozenset()) -> str:
    """Remove numbers that are the baseline of a comparison; other text is unchanged.

    A baseline followed in its clause by a calendar year that the claim names
    is the value of the claimed period ("versus 40 milhões em 2023" for a claim
    about 2023), so it is kept.
    """

    def _drop(match: re.Match[str]) -> str:
        if _CALENDAR_YEAR_RE.fullmatch(match.group("number")):
            return match.group(0)
        if claim_years and claim_years.intersection(_baseline_years(text, match.end())):
            return match.group(0)
        return f"{match.group('marker')} "

    return _BASELINE_NUMBER_RE.sub(_drop, text)


def _baseline_years(text: str, start: int) -> set[str]:
    """Calendar years that belong to the baseline ending at ``start``.

    They follow it in the same clause before any other number: in "versus 40
    milhões em 2023" the 2023 is the baseline's year; in "de 40 para 31
    milhões em 2024" the 2024 follows 31 and belongs to the current value.
    """
    end = _BASELINE_CLAUSE_END_RE.search(text, start)
    years: set[str] = set()
    for number in _NUMBER_RE.findall(text[start : end.start() if end else len(text)]):
        if not _YEAR_TOKEN_RE.fullmatch(number.strip()):
            break
        years.add(number.strip())
    return years


_PERIOD_CLAUSE_SPLIT_RE = re.compile(r"(;|\s+e\s+|\s+and\s+)", re.IGNORECASE)
_RESPECTIVELY_RE = re.compile(r"\b(?:respectivamente|respectively)\b", re.IGNORECASE)
_CLAUSE_NUMBER_RE = re.compile(r"(?<![\w-])\d+(?:[.,]\d+)*(?:\s*%)?")


_HISTORICAL_PERIOD_RE = re.compile(r"\b(?:em|desde|in|since)\s+(1\d{3})\b", re.IGNORECASE)


def _period_years(text: str) -> set[str]:
    """Calendar years of a text: 1900-2099, and earlier years after "em"/"in"."""
    years = set(_YEAR_TOKEN_RE.findall(text))
    years.update(
        year
        for year in _HISTORICAL_PERIOD_RE.findall(text)
        if _HISTORICAL_YEAR_MIN <= int(year) < _YEAR_MIN
    )
    return years


def _keep_claimed_period(evidence_text: str, claim_years: set[str]) -> str:
    """Drop the numbers of clauses that belong to another year.

    In "a receita foi de 120 milhões em 2023 e de 95 milhões em 2024" each value is
    bound to the year of its own clause, so for a claim about 2024 only "95 milhões
    em 2024" is compared. Applied only when the passage names the claimed year and
    another one, the claimed year's clause has a value of its own, and the passage
    does not pair values and years with "respectivamente". Words are kept, so
    attributes ("receita") still resolve.
    """
    evidence_years = _period_years(evidence_text)
    claimed = evidence_years & claim_years
    if not claimed or len(evidence_years) < 2 or _RESPECTIVELY_RE.search(evidence_text):
        return evidence_text
    parts = _PERIOD_CLAUSE_SPLIT_RE.split(evidence_text)
    clauses = parts[0::2]
    claimed_clause_has_value = False
    for clause in clauses:
        years = _period_years(clause)
        if years & claimed and not years - claimed:
            numbers = [n for n in _CLAUSE_NUMBER_RE.findall(clause) if n not in years]
            claimed_clause_has_value = claimed_clause_has_value or bool(numbers)
    if not claimed_clause_has_value:
        return evidence_text
    # The clause of another year is dropped. When it opens the sentence, its words
    # before the first number are kept: they carry the subject and the attribute
    # ("A receita da Vértice foi de"), so the claimed year's value stays bound to them.
    kept: list[str] = []
    for index, part in enumerate(parts):
        if index % 2:
            continue
        years = _period_years(part)
        if years and not years & claimed:
            if index == 0:
                values = [
                    match
                    for match in _CLAUSE_NUMBER_RE.finditer(part)
                    if match.group(0) not in years
                ]
                prefix = part[: values[0].start()] if values else part
                # The year of the dropped clause must not survive in its prefix.
                kept.append(_YEAR_TOKEN_RE.sub(" ", prefix) if values else "")
            continue
        kept.append(part)
    return " ".join(piece.strip() for piece in kept if piece.strip())


def _numeric_alignment(claim_text: str, evidence_text: str) -> NumericAlignment:
    """Compare every claim fact with the evidence facts (set semantics).

    A claim fact agrees when some comparable evidence fact is equal within
    tolerance, and conflicts only when comparable facts exist and none is equal.
    `unknown` attributes never match. Bare evidence numbers may confirm a claim
    fact, but only when another claim fact already agreed on a typed unit, and
    they never contradict. Each side is parsed with its own locale.
    """
    claim_entities = _entities(claim_text)
    evidence_entities = _entities(evidence_text)
    if claim_entities and not claim_entities.intersection(evidence_entities):
        return NumericAlignment(all_matched=False)

    claim_facts = _numeric_facts(claim_text)
    if not claim_facts:
        return NumericAlignment()
    claim_years = frozenset(_YEAR_TOKEN_RE.findall(claim_text))
    evidence_facts = _numeric_facts(
        _mask_comparison_baselines(
            _keep_claimed_period(evidence_text, _period_years(claim_text)), claim_years
        ),
        skip_bounds=not _has_bound(claim_text),
    )
    claim_locale = _locale_for(claim_text)
    evidence_locale = _locale_for(evidence_text)

    # Name numerals identify the entity, as "Company X" does above: when both
    # sides name an entity by numeral and the numerals differ ("Holding Três Rios"
    # vs "Holding Quatro Rios"), the evidence is about another entity.
    claim_names = {value for value, unit, _ in claim_facts if unit == "name"}
    evidence_names = {value for value, unit, _ in evidence_facts if unit == "name"}
    if claim_names - evidence_names:
        # The evidence does not name the claim's entity by its numeral ("Plano
        # Safra 2024", "Holding Três Rios"): it can neither confirm nor contradict.
        return NumericAlignment(all_matched=False)

    # Another period: the claim ties a typed fact (revenue, count, amount) to a
    # year and the evidence names only other years. "40 milhões em 2023" says
    # nothing about 2024, so it neither confirms nor contradicts the claim.
    claim_periods = {value for value, unit, _ in claim_facts if unit == "year"}
    # A year-shaped name numeral in the evidence ("Relatório Anual 2023") still
    # dates what it reports, so it counts as an evidence period here.
    evidence_periods = {
        value
        for value, unit, _ in evidence_facts
        if unit == "year" or (unit == "name" and _is_year_token(value))
    }
    claim_has_typed_fact = any(
        unit not in {"year", "name"} and attribute != "unknown"
        for _, unit, attribute in claim_facts
    )
    if (
        claim_has_typed_fact
        and claim_periods
        and evidence_periods
        and claim_periods.isdisjoint(evidence_periods)
    ):
        return NumericAlignment(all_matched=False)

    flags = {
        "specific_conflict": False,
        "generic_conflict": False,
        "specific_agreement": False,
        "generic_agreement": False,
    }
    matched = 0
    pending_confirmations = 0
    # A calendar year carries no subject: "em 2024" in a revenue claim and "em 1998"
    # in a founding date are different facts. Year conflicts are kept aside and count
    # only when the year is anchored to the claim's proposition (see below).
    year_conflicts = 0
    anchored = False
    only_years = True
    for left, left_unit, left_attribute in claim_facts:
        if left_unit == "name":
            # A numeral of the claim's name identifies the entity: it must be named
            # in the evidence, but it neither confirms nor contradicts a fact.
            matched += left in evidence_names
            continue
        left_value = _fact_value(left, left_unit, claim_locale)
        if left_value is None or left_attribute == "unknown":
            continue
        matches = [
            value
            for right, right_unit, right_attribute in evidence_facts
            if right_attribute == left_attribute and _comparable(left_unit, right_unit)
            for value in [_fact_value(right, right_unit, evidence_locale)]
            if value is not None
        ]
        if left_unit != "year":
            only_years = False
            anchored = anchored or bool(matches)
        # Calendar years, fractions and multipliers are exact; magnitudes allow
        # the ADR-002 relative tolerance.
        tolerance = Decimal(0) if left_unit in _EXACT_UNITS else DEFAULT_RELATIVE_TOLERANCE
        kind = "generic" if _is_generic(left_unit) else "specific"
        if any(relative_difference(left_value, v) <= tolerance for v in matches):
            matched += 1
            flags[f"{kind}_agreement"] = True
            continue
        if _confirmed_as_written(
            left, left_unit, claim_locale, evidence_facts, evidence_locale, tolerance
        ):
            pending_confirmations += 1
            continue
        if matches and left_unit == "year":
            # Every year of the passage is also a claimed year: the passage dates
            # only part of a compound claim ("receita em 2024 e fundação em 1987"
            # against the 2024 revenue alone). The other year is not addressed.
            if not evidence_periods <= claim_periods:
                year_conflicts += 1
        elif matches:
            matched += 1
            flags[f"{kind}_conflict"] = True
    # Anchored: another claim fact (revenue, count, amount) is compared in the same
    # evidence, or the claim states only years and shares a predicate word with it.
    if year_conflicts and (
        anchored or (only_years and _shares_predicate(claim_text, evidence_text))
    ):
        matched += year_conflicts
        flags["specific_conflict"] = True
    typed_agreement = flags["specific_agreement"] or flags["generic_agreement"]
    if typed_agreement:
        matched += pending_confirmations
    return NumericAlignment(**flags, all_matched=matched == len(claim_facts))


def _confirmed_as_written(
    left: str,
    left_unit: str,
    claim_locale: NumericLocale,
    evidence_facts: list[tuple[str, str, str]],
    evidence_locale: NumericLocale,
    tolerance: Decimal,
) -> bool:
    """A claim duration/scalar equals a bare evidence number as written.

    A scaled claim value ("40 milhões") is confirmed by a scaled evidence value
    of the same magnitude whose attribute could not be resolved ("versus 40
    milhões em 2023"), exactly as a bare scalar was before scales were read.
    """
    scaled = left_unit.startswith("scaled:")
    if not (left_unit.startswith("duration:") or left_unit == "scalar" or scaled):
        return False
    written = _fact_value(left, left_unit, claim_locale, as_written=True)
    if written is None:
        return False
    for right, right_unit, _ in evidence_facts:
        if scaled:
            if not right_unit.startswith("scaled:"):
                continue
        elif right_unit.startswith("duration:"):
            # Two values with units were already compared after normalization:
            # "120 kW" never confirms "120 MW", nor "15 horas" "15 dias", as written.
            if left_unit.startswith("duration:"):
                continue
        elif right_unit not in {"scalar", "year"}:
            continue
        value = _fact_value(right, right_unit, evidence_locale, as_written=True)
        if value is not None and relative_difference(written, value) <= tolerance:
            return True
    return False


def _numeric_facts_align(claim_text: str, evidence_text: str) -> tuple[bool, bool, bool]:
    """Return (conflict, agreement, every_claim_fact_matched)."""
    alignment = _numeric_alignment(claim_text, evidence_text)
    return alignment.conflict, alignment.agreement, alignment.all_matched


def _numeric_conflict(claim_text: str, evidence_text: str) -> bool:
    return _numeric_relation(claim_text, evidence_text)[0]


def _numeric_agreement(claim_text: str, evidence_text: str) -> bool:
    return _numeric_relation(claim_text, evidence_text)[1]


@dataclass(frozen=True)
class DetectedStance:
    edge: StanceEdge
    confidence: float
    provenance: ComponentProvenance


@dataclass(frozen=True)
class StanceDetectionResult:
    edges: tuple[DetectedStance, ...]


class StanceDetector(Protocol):
    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult: ...


class RuleStanceDetector:
    component = "stance_detector.rule"
    model = "rule-fixture"
    version = "16"

    @staticmethod
    def _numeric_conflict(claim_text: str, evidence_text: str) -> bool:
        return _numeric_conflict(claim_text, evidence_text)

    @staticmethod
    def _date_conflict(claim_text: str, evidence_text: str) -> bool:
        return _dates_conflict(claim_text, evidence_text)

    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        output = []
        for claim_item in claims:
            claim_tokens = {
                token.casefold()
                for token in _TOKEN_RE.findall(claim_item.claim.text)
                if len(token) > 2
            }
            for item in (x for x in evidence if x.claim_id == claim_item.claim.id):
                evidence_tokens = {
                    token.casefold() for token in _TOKEN_RE.findall(item.excerpt) if len(token) > 2
                }
                lexical = len(claim_tokens & evidence_tokens) / max(len(claim_tokens), 1)
                alignment = _numeric_alignment(claim_item.claim.text, item.excerpt)
                # Generic units (durations, fractions, measures) carry no subject:
                # they decide only when claim and evidence share the proposition.
                shares_proposition = _content_overlap(claim_item.claim.text, item.excerpt) >= 0.25
                numeric_conflict = alignment.specific_conflict or (
                    alignment.generic_conflict and shares_proposition
                )
                numeric_agreement = alignment.specific_agreement or (
                    alignment.generic_agreement and shares_proposition
                )
                numeric_matched = alignment.all_matched
                claim_facts = _numeric_facts(claim_item.claim.text)
                claim_has_numeric = any(unit != "name" for _, unit, _ in claim_facts)
                # A numeral of a name ("Holding Três Rios") is not a quantity, but
                # evidence about another name ("Holding Quatro Rios") is unverified.
                claim_name_unmatched = not numeric_matched and any(
                    unit == "name" for _, unit, _ in claim_facts
                )
                claim_has_date = bool(_extract_dates(claim_item.claim.text))
                claim_entities = _entities(claim_item.claim.text)
                evidence_entities = _entities(item.excerpt)
                entity_mismatch = bool(
                    claim_entities and not claim_entities.intersection(evidence_entities)
                ) or _competing_entity(claim_item.claim.text, item.excerpt)
                # Another named actor, a part of the entity or a longer-named sibling:
                # the passage reports another entity, so it cannot contradict either.
                other_entity = _competing_entity(
                    claim_item.claim.text, item.excerpt
                ) or _entity_variant(claim_item.claim.text, item.excerpt)
                entity_mismatch = entity_mismatch or other_entity
                date_conflict = self._date_conflict(claim_item.claim.text, item.excerpt)
                evidence_has_date = bool(_extract_dates(item.excerpt))
                negation_conflict = _has_negation(claim_item.claim.text) != _has_negation(
                    item.excerpt, frozenset(claim_tokens)
                )
                direction_conflict = _direction_conflict(claim_item.claim.text, item.excerpt)
                unverified_structured_fact = (
                    (claim_has_numeric and (not numeric_matched or not numeric_agreement))
                    or claim_name_unmatched
                    or (claim_has_date and not evidence_has_date)
                    or entity_mismatch
                )
                # Numeric conflicts are already gated by attribute/entity alignment.
                # Polarity and date mismatches only count when claim and evidence
                # describe the same proposition; otherwise they are unrelated text.
                same_proposition = lexical >= 0.25
                if _reported_denial(item.excerpt, frozenset(claim_tokens)) or _non_assertive(
                    item.excerpt, frozenset(claim_tokens)
                ):
                    # "X negou que P", "P pode ter ocorrido", "estima-se que P",
                    # "não se sabe se P": the document neither asserts P nor
                    # establishes that P is false.
                    stance = Stance.NEUTRAL
                elif other_entity:
                    stance = Stance.NEUTRAL
                elif numeric_conflict or (
                    same_proposition and (date_conflict or negation_conflict or direction_conflict)
                ):
                    stance = Stance.CONTRADICTS
                elif unverified_structured_fact:
                    stance = Stance.NEUTRAL
                elif numeric_agreement:
                    stance = Stance.SUPPORTS
                elif lexical < 0.25:
                    stance = Stance.NEUTRAL
                else:
                    stance = Stance.SUPPORTS
                payload = f"{claim_item.claim.id}|{item.id}|{stance.value}"
                output.append(
                    DetectedStance(
                        StanceEdge(
                            id=f"ste_{claim_item.claim.id}_{item.id}",
                            claim_id=claim_item.claim.id,
                            evidence_id=item.id,
                            stance=stance,
                        ),
                        min(1.0, max(0.5, 0.5 + lexical / 2)),
                        ComponentProvenance(
                            self.component,
                            self.model,
                            self.version,
                            _sha256(claim_item.claim.text + "\n" + item.excerpt),
                            _sha256(payload),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))


class NLIStanceDetector(StanceDetector):
    component = "stance_detector.nli"

    def __init__(
        self,
        backend: Any,
        *,
        model: str,
        version: str,
        window_size: int = 512,
        window_overlap: int = 64,
        tie_precedence: str = "contradicts",
    ) -> None:
        if window_size <= 0 or window_overlap < 0 or window_overlap >= window_size:
            raise ValueError("invalid evidence window configuration")
        if tie_precedence not in {"contradicts", "supports", "neutral"}:
            raise ValueError("invalid stance tie precedence")
        self.backend = backend
        self.model = model
        self.version = version
        self.window_size = window_size
        self.window_overlap = window_overlap
        self.tie_precedence = tie_precedence

    def _windows(self, evidence: Evidence) -> list[tuple[int, int, str]]:
        text = evidence.excerpt
        if len(text) <= self.window_size:
            return [(evidence.start_offset, evidence.end_offset, text)]
        step = self.window_size - self.window_overlap
        windows = []
        for start in range(0, len(text), step):
            end = min(len(text), start + self.window_size)
            windows.append(
                (evidence.start_offset + start, evidence.start_offset + end, text[start:end])
            )
            if end == len(text):
                break
        return windows

    def _choose(
        self,
        candidates: list[tuple[str, float, int, int]],
    ) -> tuple[str, float, int, int]:
        priority = {"contradicts": 2, "supports": 1, "neutral": 0}
        if self.tie_precedence == "supports":
            priority["supports"] = 3
        elif self.tie_precedence == "neutral":
            priority["neutral"] = 3
        return max(candidates, key=lambda item: (item[1], priority[item[0]]))

    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        output = []
        for claim_item in claims:
            for item in (x for x in evidence if x.claim_id == claim_item.claim.id):
                candidates = []
                for start, end, window in self._windows(item):
                    result = self.backend.classify(claim_item.claim.text, window)
                    candidates.append(
                        (
                            str(result["stance"]),
                            float(result["confidence"]),
                            start,
                            end,
                        )
                    )
                stance, confidence, start, end = self._choose(candidates)
                local_start = start - item.start_offset
                local_end = end - item.start_offset
                output.append(
                    DetectedStance(
                        StanceEdge(
                            id=f"ste_{claim_item.claim.id}_{item.id}",
                            claim_id=claim_item.claim.id,
                            evidence_id=item.id,
                            stance=Stance(stance),
                        ),
                        confidence,
                        ComponentProvenance(
                            self.component,
                            self.model,
                            f"{self.version}|window={start}:{end}",
                            _sha256(
                                claim_item.claim.text + "\n" + item.excerpt[local_start:local_end]
                            ),
                            _sha256(f"{stance}|{confidence:.12f}|{start}|{end}"),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))


class TranslatedNLIStanceDetector(NLIStanceDetector):
    component = "stance_detector.translate_nli"

    def __init__(
        self,
        backend: Any,
        translator: Any,
        *,
        model: str,
        version: str,
        window_size: int = 512,
        window_overlap: int = 64,
        tie_precedence: str = "contradicts",
    ) -> None:
        super().__init__(
            backend,
            model=model,
            version=version,
            window_size=window_size,
            window_overlap=window_overlap,
            tie_precedence=tie_precedence,
        )
        self.translator = translator

    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        output = []
        for claim_item in claims:
            for item in (x for x in evidence if x.claim_id == claim_item.claim.id):
                claim = claim_item.claim.text
                document = item.excerpt
                claim_lang = detect_language(claim)
                document_lang = detect_language(document)
                translated_claim = claim
                translated_document = document
                translation_hash = "none"
                if claim_lang != document_lang:
                    if claim_lang == "pt":
                        translated_claim = self.translator.translate(claim)
                        translation_hash = self.translator.provenance_hash(claim, translated_claim)
                    elif document_lang == "pt":
                        translated_document = self.translator.translate(document)
                        translation_hash = self.translator.provenance_hash(
                            document, translated_document
                        )
                temp_evidence = item.model_copy(update={"excerpt": translated_document})
                candidates = []
                for start, end, window in self._windows(temp_evidence):
                    result = self.backend.classify(translated_claim, window)
                    candidates.append(
                        (
                            str(result["stance"]),
                            float(result["confidence"]),
                            start,
                            end,
                        )
                    )
                stance, confidence, start, end = self._choose(candidates)
                if translated_document != document:
                    # Translation has no character alignment contract. Never expose
                    # translated-text offsets as if they were source-document offsets.
                    provenance_start = item.start_offset
                    provenance_end = item.end_offset
                    provenance_excerpt = document
                else:
                    provenance_start = start
                    provenance_end = end
                    local_start = start - temp_evidence.start_offset
                    local_end = end - temp_evidence.start_offset
                    provenance_excerpt = document[local_start:local_end]
                provenance_input = translated_claim + "\n" + provenance_excerpt
                output.append(
                    DetectedStance(
                        StanceEdge(
                            id=f"ste_{claim_item.claim.id}_{item.id}",
                            claim_id=claim_item.claim.id,
                            evidence_id=item.id,
                            stance=Stance(stance),
                        ),
                        confidence,
                        ComponentProvenance(
                            self.component,
                            self.model,
                            f"{self.version}|window={provenance_start}:{provenance_end}|"
                            f"translation={translation_hash}",
                            _sha256(provenance_input),
                            _sha256(
                                f"{stance}|{confidence:.12f}|{provenance_start}|"
                                f"{provenance_end}|{translation_hash}"
                            ),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))


def _sentence_windows(evidence: Evidence) -> list[tuple[int, int, str]]:
    text = evidence.excerpt
    spans: list[tuple[int, int, str]] = []
    start = 0
    for match in re.finditer(r"[.!?](?:[\"”’)]*)?(?=\s|$)", text):
        end = match.end()
        raw = text[start:end]
        left = start + len(raw) - len(raw.lstrip())
        right = start + len(raw.rstrip())
        if left < right:
            spans.append(
                (
                    evidence.start_offset + left,
                    evidence.start_offset + right,
                    text[left:right],
                )
            )
        start = end
        while start < len(text) and text[start].isspace():
            start += 1
    if start < len(text):
        spans.append((evidence.start_offset + start, evidence.end_offset, text[start:]))
    if not spans:
        spans.append((evidence.start_offset, evidence.end_offset, text))
    return spans


class SentenceNLIStanceDetector(NLIStanceDetector):
    """H1: evaluate claim against deterministic sentence spans."""

    component = "stance_detector.nli_sentence"

    def _windows(self, evidence: Evidence) -> list[tuple[int, int, str]]:
        return _sentence_windows(evidence)


class SentenceTranslatedNLIStanceDetector(TranslatedNLIStanceDetector):
    """H1 translated path: sentence aggregation with the E1 translation contract."""

    component = "stance_detector.translate_nli_sentence"

    def _windows(self, evidence: Evidence) -> list[tuple[int, int, str]]:
        return _sentence_windows(evidence)


class LLMStanceDetector:
    component = "stance_detector.llm"

    def __init__(self, provider: Any, *, model: str, version: str) -> None:
        self.provider, self.model, self.version = provider, model, version

    def detect(
        self,
        claims: Sequence[ExtractedClaim],
        evidence: Sequence[Evidence],
    ) -> StanceDetectionResult:
        import json

        output = []
        for claim_item in claims:
            for item in (x for x in evidence if x.claim_id == claim_item.claim.id):
                prompt = json.dumps(
                    {
                        "task": "classify stance only",
                        "claim": claim_item.claim.text,
                        "evidence": item.excerpt,
                        "allowed_stance": ["supports", "contradicts", "neutral"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                response = self.provider.execute(prompt)
                try:
                    result = LLMStancePayload.model_validate(json.loads(response.text))
                except Exception as exc:
                    raise ValueError(f"invalid stance payload: {exc}") from exc
                if result.evidence_id != item.id:
                    raise ValueError(f"unknown evidence id: {result.evidence_id}")
                output.append(
                    DetectedStance(
                        StanceEdge(
                            id=f"ste_{claim_item.claim.id}_{item.id}",
                            claim_id=claim_item.claim.id,
                            evidence_id=item.id,
                            stance=Stance(result.stance),
                        ),
                        result.confidence,
                        ComponentProvenance(
                            self.component,
                            self.model,
                            self.version,
                            _sha256(prompt),
                            _sha256(response.text),
                        ),
                    )
                )
        return StanceDetectionResult(tuple(output))
