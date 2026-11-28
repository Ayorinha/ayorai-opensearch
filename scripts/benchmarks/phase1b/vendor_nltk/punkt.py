# Vendored from nltk 3.9.4 (Apache License 2.0, see LICENSE.txt in this directory).
# Edits are listed in README.md; everything else is byte-identical to upstream.
#
# Natural Language Toolkit: Punkt sentence tokenizer
#
# Copyright (C) 2001-2026 NLTK Project
# Algorithm: Kiss & Strunk (2006)
# Author: Willy <willy@csse.unimelb.edu.au> (original Python port)
#         Steven Bird <stevenbird1@gmail.com> (additions)
#         Edward Loper <edloper@gmail.com> (rewrite)
#         Joel Nothman <jnothman@student.usyd.edu.au> (almost rewrite)
#         Arthur Darcet <arthur@darcet.fr> (fixes)
#         Tom Aarsen <> (tackle ReDoS & performance issues)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

r"""
Punkt Sentence Tokenizer

This tokenizer divides a text into a list of sentences
by using an unsupervised algorithm to build a model for abbreviation
words, collocations, and words that start sentences.  It must be
trained on a large collection of plaintext in the target language
before it can be used.

The NLTK data package includes a pre-trained Punkt tokenizer for
English.

    >>> from nltk.tokenize import PunktTokenizer
    >>> text = '''
    ... Punkt knows that the periods in Mr. Smith and Johann S. Bach
    ... do not mark sentence boundaries.  And sometimes sentences
    ... can start with non-capitalized words.  i is a good variable
    ... name.
    ... '''
    >>> sent_detector = PunktTokenizer()
    >>> print('\n-----\n'.join(sent_detector.tokenize(text.strip())))
    Punkt knows that the periods in Mr. Smith and Johann S. Bach
    do not mark sentence boundaries.
    -----
    And sometimes sentences
    can start with non-capitalized words.
    -----
    i is a good variable
    name.

(Note that whitespace from the original text, including newlines, is
retained in the output.)

Punctuation following sentences is also included by default
(from NLTK 3.0 onwards). It can be excluded with the realign_boundaries
flag.

    >>> text = '''
    ... (How does it deal with this parenthesis?)  "It should be part of the
    ... previous sentence." "(And the same with this one.)" ('And this one!')
    ... "('(And (this)) '?)" [(and this. )]
    ... '''
    >>> print('\n-----\n'.join(
    ...     sent_detector.tokenize(text.strip())))
    (How does it deal with this parenthesis?)
    -----
    "It should be part of the
    previous sentence."
    -----
    "(And the same with this one.)"
    -----
    ('And this one!')
    -----
    "('(And (this)) '?)"
    -----
    [(and this. )]
    >>> print('\n-----\n'.join(
    ...     sent_detector.tokenize(text.strip(), realign_boundaries=False)))
    (How does it deal with this parenthesis?
    -----
    )  "It should be part of the
    previous sentence.
    -----
    " "(And the same with this one.
    -----
    )" ('And this one!
    -----
    ')
    "('(And (this)) '?
    -----
    )" [(and this.
    -----
    )]

However, Punkt is designed to learn parameters (a list of abbreviations, etc.)
unsupervised from a corpus similar to the target domain. The pre-packaged models
may therefore be unsuitable: use ``PunktSentenceTokenizer(text)`` to learn
parameters from the given text.

:class:`.PunktTrainer` learns parameters such as a list of abbreviations
(without supervision) from portions of text. Using a ``PunktTrainer`` directly
allows for incremental training and modification of the hyper-parameters used
to decide what is considered an abbreviation, etc.

The algorithm for this tokenizer is described in::

  Kiss, Tibor and Strunk, Jan (2006): Unsupervised Multilingual Sentence
    Boundary Detection.  Computational Linguistics 32: 485-525.
"""

# TODO: Make orthographic heuristic less susceptible to overtraining
# TODO: Frequent sentence starters optionally exclude always-capitalised words
# FIXME: Problem with ending string with e.g. '!!!' -> '!! !'

import math
import re
import string
from collections import defaultdict
from collections.abc import Iterator
from re import Match
from typing import Any, Dict, List, Optional, Tuple, Union

from ._api import TokenizerI

######################################################################
# { Orthographic Context Constants
######################################################################
# The following constants are used to describe the orthographic
# contexts in which a word can occur.  BEG=beginning, MID=middle,
# UNK=unknown, UC=uppercase, LC=lowercase, NC=no case.

_ORTHO_BEG_UC = 1 << 1
"""Orthographic context: beginning of a sentence with upper case."""

_ORTHO_MID_UC = 1 << 2
"""Orthographic context: middle of a sentence with upper case."""

_ORTHO_UNK_UC = 1 << 3
"""Orthographic context: unknown position in a sentence with upper case."""

_ORTHO_BEG_LC = 1 << 4
"""Orthographic context: beginning of a sentence with lower case."""

_ORTHO_MID_LC = 1 << 5
"""Orthographic context: middle of a sentence with lower case."""

_ORTHO_UNK_LC = 1 << 6
"""Orthographic context: unknown position in a sentence with lower case."""

_ORTHO_UC = _ORTHO_BEG_UC + _ORTHO_MID_UC + _ORTHO_UNK_UC
"""Orthographic context: occurs with upper case."""

_ORTHO_LC = _ORTHO_BEG_LC + _ORTHO_MID_LC + _ORTHO_UNK_LC
"""Orthographic context: occurs with lower case."""

_ORTHO_MAP = {
    ("initial", "upper"): _ORTHO_BEG_UC,
    ("internal", "upper"): _ORTHO_MID_UC,
    ("unknown", "upper"): _ORTHO_UNK_UC,
    ("initial", "lower"): _ORTHO_BEG_LC,
    ("internal", "lower"): _ORTHO_MID_LC,
    ("unknown", "lower"): _ORTHO_UNK_LC,
}
"""A map from context position and first-letter case to the
appropriate orthographic context flag."""

# } (end orthographic context constants)
######################################################################

######################################################################
# { Decision reasons for debugging
######################################################################

REASON_DEFAULT_DECISION = "default decision"
REASON_KNOWN_COLLOCATION = "known collocation (both words)"
REASON_ABBR_WITH_ORTHOGRAPHIC_HEURISTIC = "abbreviation + orthographic heuristic"
REASON_ABBR_WITH_SENTENCE_STARTER = "abbreviation + frequent sentence starter"
REASON_INITIAL_WITH_ORTHOGRAPHIC_HEURISTIC = "initial + orthographic heuristic"
REASON_NUMBER_WITH_ORTHOGRAPHIC_HEURISTIC = "initial + orthographic heuristic"
REASON_INITIAL_WITH_SPECIAL_ORTHOGRAPHIC_HEURISTIC = (
    "initial + special orthographic heuristic"
)


# } (end decision reasons for debugging)
######################################################################

######################################################################
# { Language-dependent variables
######################################################################


class PunktLanguageVars:
    """
    Stores variables, mostly regular expressions, which may be
    language-dependent for correct application of the algorithm.
    An extension of this class may modify its properties to suit
    a language other than English; an instance can then be passed
    as an argument to PunktSentenceTokenizer and PunktTrainer
    constructors.
    """

    __slots__ = ("_re_period_context", "_re_word_tokenizer")

    def __getstate__(self):
        # All modifications to the class are performed by inheritance.
        # Non-default parameters to be saved must be defined in the inherited
        # class.
        return 1

    def __setstate__(self, state):
        return 1

    sent_end_chars = (".", "?", "!")
    """Characters which are candidates for sentence boundaries"""

    @property
    def _re_sent_end_chars(self):
        return "[%s]" % re.escape("".join(self.sent_end_chars))

    internal_punctuation = ",:;"  # might want to extend this..
    """sentence internal punctuation, which indicates an abbreviation if
    preceded by a period-final token."""

    re_boundary_realignment = re.compile(r'["\')\]}]+?(?:\s+|(?=--)|$)', re.MULTILINE)
    """Used to realign punctuation that should be included in a sentence
    although it follows the period (or ?, !)."""

    _re_word_start = r"[^\(\"\`{\[:;&\#\*@\)}\]\-,]"
    """Excludes some characters from starting word tokens"""

    @property
    def _re_non_word_chars(self):
        return r"(?:[)\";}\]\*:@\'\({\[%s])" % re.escape(
            "".join(set(self.sent_end_chars) - {"."})
        )

    """Characters that cannot appear within words"""

    _re_multi_char_punct = r"(?:\-{2,}|\.{2,}|(?:\.\s){2,}\.)"
    """Hyphen and ellipsis are multi-character punctuation"""

    _word_tokenize_fmt = r"""(
        %(MultiChar)s
        |
        (?=%(WordStart)s)\S+?  # Accept word characters until end is found
        (?= # Sequences marking a word's end
            \s|                                 # White-space
            $|                                  # End-of-string
            %(NonWord)s|%(MultiChar)s|          # Punctuation
            ,(?=$|\s|%(NonWord)s|%(MultiChar)s) # Comma if at end of word
        )
        |
        \S
    )"""
    """Format of a regular expression to split punctuation from words,
    excluding period."""

    def _word_tokenizer_re(self):
        """Compiles and returns a regular expression for word tokenization"""
        try:
            return self._re_word_tokenizer
        except AttributeError:
            self._re_word_tokenizer = re.compile(
                self._word_tokenize_fmt
                % {
                    "NonWord": self._re_non_word_chars,
                    "MultiChar": self._re_multi_char_punct,
                    "WordStart": self._re_word_start,
                },
                re.UNICODE | re.VERBOSE,
            )
            return self._re_word_tokenizer

    def word_tokenize(self, s):
        """Tokenize a string to split off punctuation other than periods"""
        return self._word_tokenizer_re().findall(s)

    _period_context_fmt = r"""
        %(SentEndChars)s             # a potential sentence ending
        (?=(?P<after_tok>
            %(NonWord)s              # either other punctuation
            |
            \s+(?P<next_tok>\S+)     # or whitespace and some other token
        ))"""
    """Format of a regular expression to find contexts including possible
    sentence boundaries. Matches token which the possible sentence boundary
    ends, and matches the following token within a lookahead expression."""

    def period_context_re(self):
        """Compiles and returns a regular expression to find contexts
        including possible sentence boundaries."""
        try:
            return self._re_period_context
        except AttributeError:
            self._re_period_context = re.compile(
                self._period_context_fmt
                % {
                    "NonWord": self._re_non_word_chars,
                    "SentEndChars": self._re_sent_end_chars,
                },
                re.UNICODE | re.VERBOSE,
            )
            return self._re_period_context


_re_non_punct = re.compile(r"[^\W\d]", re.UNICODE)
"""Matches token types that are not merely punctuation. (Types for
numeric tokens are changed to ##number## and hence contain alpha.)"""


# }
######################################################################


# ////////////////////////////////////////////////////////////
# { Helper Functions
# ////////////////////////////////////////////////////////////


def _pair_iter(iterator):
    """
    Yields pairs of tokens from the given iterator such that each input
    token will appear as the first element in a yielded tuple. The last
    pair will have None as its second element.
    """
    iterator = iter(iterator)
    try:
        prev = next(iterator)
    except StopIteration:
        return
    for el in iterator:
        yield (prev, el)
        prev = el
    yield (prev, None)


######################################################################
# { Punkt Parameters
######################################################################


class PunktParameters:
    """Stores data used to perform sentence boundary detection with Punkt."""

    def __init__(self):
        self.abbrev_types = set()
        """A set of word types for known abbreviations."""

        self.collocations = set()
        """A set of word type tuples for known common collocations
        where the first word ends in a period.  E.g., ('S.', 'Bach')
        is a common collocation in a text that discusses 'Johann
        S. Bach'.  These count as negative evidence for sentence
        boundaries."""

        self.sent_starters = set()
        """A set of word types for words that often appear at the
        beginning of sentences."""

        self.ortho_context = defaultdict(int)
        """A dictionary mapping word types to the set of orthographic
        contexts that word type appears in.  Contexts are represented
        by adding orthographic context flags: ..."""

    def clear_abbrevs(self):
        self.abbrev_types = set()

    def clear_collocations(self):
        self.collocations = set()

    def clear_sent_starters(self):
        self.sent_starters = set()

    def clear_ortho_context(self):
        self.ortho_context = defaultdict(int)

    def add_ortho_context(self, typ, flag):
        self.ortho_context[typ] |= flag

    def _debug_ortho_context(self, typ):
        context = self.ortho_context[typ]
        if context & _ORTHO_BEG_UC:
            yield "BEG-UC"
        if context & _ORTHO_MID_UC:
            yield "MID-UC"
        if context & _ORTHO_UNK_UC:
            yield "UNK-UC"
        if context & _ORTHO_BEG_LC:
            yield "BEG-LC"
        if context & _ORTHO_MID_LC:
            yield "MID-LC"
        if context & _ORTHO_UNK_LC:
            yield "UNK-LC"


######################################################################
# { PunktToken
######################################################################


class PunktToken:
    """Stores a token of text with annotations produced during
    sentence boundary detection."""

    _properties = ["parastart", "linestart", "sentbreak", "abbr", "ellipsis"]
    __slots__ = ["tok", "type", "period_final"] + _properties

    def __init__(self, tok, **params):
        self.tok = tok
        self.type = self._get_type(tok)
        self.period_final = tok.endswith(".")

        for prop in self._properties:
            setattr(self, prop, None)
        for k in params:
            setattr(self, k, params[k])

    # ////////////////////////////////////////////////////////////
    # { Regular expressions for properties
    # ////////////////////////////////////////////////////////////
    # Note: [A-Za-z] is approximated by [^\W\d] in the general case.
    _RE_ELLIPSIS = re.compile(r"\.\.+$")
    _RE_NUMERIC = re.compile(r"^-?[\.,]?\d[\d,\.-]*\.?$")
    _RE_INITIAL = re.compile(r"[^\W\d]\.$", re.UNICODE)
    _RE_ALPHA = re.compile(r"[^\W\d]+$", re.UNICODE)

    # ////////////////////////////////////////////////////////////
    # { Derived properties
    # ////////////////////////////////////////////////////////////

    def _get_type(self, tok):
        """Returns a case-normalized representation of the token."""
        return self._RE_NUMERIC.sub("##number##", tok.lower())

    @property
    def type_no_period(self):
        """
        The type with its final period removed if it has one.
        """
        if len(self.type) > 1 and self.type[-1] == ".":
            return self.type[:-1]
        return self.type

    @property
    def type_no_sentperiod(self):
        """
        The type with its final period removed if it is marked as a
        sentence break.
        """
        if self.sentbreak:
            return self.type_no_period
        return self.type

    @property
    def first_upper(self):
        """True if the token's first character is uppercase."""
        return self.tok[0].isupper()

    @property
    def first_lower(self):
        """True if the token's first character is lowercase."""
        return self.tok[0].islower()

    @property
    def first_case(self):
        if self.first_lower:
            return "lower"
        if self.first_upper:
            return "upper"
        return "none"

    @property
    def is_ellipsis(self):
        """True if the token text is that of an ellipsis."""
        return self._RE_ELLIPSIS.match(self.tok)

    @property
    def is_number(self):
        """True if the token text is that of a number."""
        return self.type.startswith("##number##")

    @property
    def is_initial(self):
        """True if the token text is that of an initial."""
        return self._RE_INITIAL.match(self.tok)

    @property
    def is_alpha(self):
        """True if the token text is all alphabetic."""
        return self._RE_ALPHA.match(self.tok)

    @property
    def is_non_punct(self):
        """True if the token is either a number or is alphabetic."""
        return _re_non_punct.search(self.type)

    # ////////////////////////////////////////////////////////////
    # { String representation
    # ////////////////////////////////////////////////////////////

    def __repr__(self):
        """
        A string representation of the token that can reproduce it
        with eval(), which lists all the token's non-default
        annotations.
        """
        typestr = " type=%s," % repr(self.type) if self.type != self.tok else ""

        propvals = ", ".join(
            f"{p}={repr(getattr(self, p))}"
            for p in self._properties
            if getattr(self, p)
        )

        return "{}({},{} {})".format(
            self.__class__.__name__,
            repr(self.tok),
            typestr,
            propvals,
        )

    def __str__(self):
        """
        A string representation akin to that used by Kiss and Strunk.
        """
        res = self.tok
        if self.abbr:
            res += "<A>"
        if self.ellipsis:
            res += "<E>"
        if self.sentbreak:
            res += "<S>"
        return res


######################################################################
# { Punkt base class
######################################################################


class PunktBaseClass:
    """
    Includes common components of PunktTrainer and PunktSentenceTokenizer.
    """

    def __init__(self, lang_vars=None, token_cls=PunktToken, params=None):
        if lang_vars is None:
            lang_vars = PunktLanguageVars()
        if params is None:
            params = PunktParameters()
        self._params = params
        self._lang_vars = lang_vars
        self._Token = token_cls
        """The collection of parameters that determines the behavior
        of the punkt tokenizer."""

    # ////////////////////////////////////////////////////////////
    # { Word tokenization
    # ////////////////////////////////////////////////////////////

    def _tokenize_words(self, plaintext):
        """
        Divide the given text into tokens, using the punkt word
        segmentation regular expression, and generate the resulting list
        of tokens augmented as three-tuples with two boolean values for whether
        the given token occurs at the start of a paragraph or a new line,
        respectively.
        """
        parastart = False
        for line in plaintext.split("\n"):
            if line.strip():
                line_toks = iter(self._lang_vars.word_tokenize(line))

                try:
                    tok = next(line_toks)
                except StopIteration:
                    continue

                yield self._Token(tok, parastart=parastart, linestart=True)
                parastart = False

                for tok in line_toks:
                    yield self._Token(tok)
            else:
                parastart = True

    # ////////////////////////////////////////////////////////////
    # { Annotation Procedures
    # ////////////////////////////////////////////////////////////

    def _annotate_first_pass(
        self, tokens: Iterator[PunktToken]
    ) -> Iterator[PunktToken]:
        """
        Perform the first pass of annotation, which makes decisions
        based purely based on the word type of each word:

          - '?', '!', and '.' are marked as sentence breaks.
          - sequences of two or more periods are marked as ellipsis.
          - any word ending in '.' that's a known abbreviation is
            marked as an abbreviation.
          - any other word ending in '.' is marked as a sentence break.

        Return these annotations as a tuple of three sets:

          - sentbreak_toks: The indices of all sentence breaks.
          - abbrev_toks: The indices of all abbreviations.
          - ellipsis_toks: The indices of all ellipsis marks.
        """
        for aug_tok in tokens:
            self._first_pass_annotation(aug_tok)
            yield aug_tok

    def _first_pass_annotation(self, aug_tok: PunktToken) -> None:
        """
        Performs type-based annotation on a single token.
        """

        tok = aug_tok.tok

        if tok in self._lang_vars.sent_end_chars:
            aug_tok.sentbreak = True
        elif aug_tok.is_ellipsis:
            aug_tok.ellipsis = True
        elif aug_tok.period_final and not tok.endswith(".."):
            if (
                tok[:-1].lower() in self._params.abbrev_types
                or tok[:-1].lower().split("-")[-1] in self._params.abbrev_types
            ):
                aug_tok.abbr = True
            else:
                aug_tok.sentbreak = True

        return


######################################################################
# { Punkt Sentence Tokenizer
######################################################################


class PunktSentenceTokenizer(PunktBaseClass, TokenizerI):
    """
    A sentence tokenizer which uses an unsupervised algorithm to build
    a model for abbreviation words, collocations, and words that start
    sentences; and then uses that model to find sentence boundaries.
    This approach has been shown to work well for many European
    languages.
    """

    def __init__(
        self, train_text=None, verbose=False, lang_vars=None, token_cls=PunktToken
    ):
        """
        train_text can either be the sole training text for this sentence
        boundary detector, or can be a PunktParameters object.
        """
        PunktBaseClass.__init__(self, lang_vars=lang_vars, token_cls=token_cls)

        if train_text:
            self._params = self.train(train_text, verbose)

    def train(self, train_text, verbose=False):
        """
        Derives parameters from a given training text, or uses the parameters
        given. Repeated calls to this method destroy previous parameters. For
        incremental training, instantiate a separate PunktTrainer instance.
        """
        if not isinstance(train_text, str):
            return train_text
        raise NotImplementedError("Punkt training is not part of the vendored subset")

    # ////////////////////////////////////////////////////////////
    # { Tokenization
    # ////////////////////////////////////////////////////////////

    def tokenize(self, text: str, realign_boundaries: bool = True) -> list[str]:
        """
        Given a text, returns a list of the sentences in that text.
        """
        return list(self.sentences_from_text(text, realign_boundaries))

    def debug_decisions(self, text: str) -> Iterator[dict[str, Any]]:
        """
        Classifies candidate periods as sentence breaks, yielding a dict for
        each that may be used to understand why the decision was made.

        See format_debug_decision() to help make this output readable.
        """

        for match, decision_text in self._match_potential_end_contexts(text):
            tokens = self._tokenize_words(decision_text)
            tokens = list(self._annotate_first_pass(tokens))
            while tokens and not tokens[0].tok.endswith(self._lang_vars.sent_end_chars):
                tokens.pop(0)
            yield {
                "period_index": match.end() - 1,
                "text": decision_text,
                "type1": tokens[0].type,
                "type2": tokens[1].type,
                "type1_in_abbrs": bool(tokens[0].abbr),
                "type1_is_initial": bool(tokens[0].is_initial),
                "type2_is_sent_starter": tokens[1].type_no_sentperiod
                in self._params.sent_starters,
                "type2_ortho_heuristic": self._ortho_heuristic(tokens[1]),
                "type2_ortho_contexts": set(
                    self._params._debug_ortho_context(tokens[1].type_no_sentperiod)
                ),
                "collocation": (
                    tokens[0].type_no_sentperiod,
                    tokens[1].type_no_sentperiod,
                )
                in self._params.collocations,
                "reason": self._second_pass_annotation(tokens[0], tokens[1])
                or REASON_DEFAULT_DECISION,
                "break_decision": tokens[0].sentbreak,
            }

    def span_tokenize(
        self, text: str, realign_boundaries: bool = True
    ) -> Iterator[tuple[int, int]]:
        """
        Given a text, generates (start, end) spans of sentences
        in the text.
        """
        slices = self._slices_from_text(text)
        if realign_boundaries:
            slices = self._realign_boundaries(text, slices)
        for sentence in slices:
            yield (sentence.start, sentence.stop)

    def sentences_from_text(
        self, text: str, realign_boundaries: bool = True
    ) -> list[str]:
        """
        Given a text, generates the sentences in that text by only
        testing candidate sentence breaks. If realign_boundaries is
        True, includes in the sentence closing punctuation that
        follows the period.
        """
        return [text[s:e] for s, e in self.span_tokenize(text, realign_boundaries)]

    def _get_last_whitespace_index(self, text: str) -> int:
        """
        Given a text, find the index of the *last* occurrence of *any*
        whitespace character, i.e. " ", "\n", "\t", "\r", etc.
        If none is found, return 0.
        """
        for i in range(len(text) - 1, -1, -1):
            if text[i] in string.whitespace:
                return i
        return 0

    def _match_potential_end_contexts(self, text: str) -> Iterator[tuple[Match, str]]:
        """
        Given a text, find the matches of potential sentence breaks,
        alongside the contexts surrounding these sentence breaks.

        Since the fix for the ReDOS discovered in issue #2866, we no longer match
        the word before a potential end of sentence token. Instead, we use a separate
        regex for this. As a consequence, `finditer`'s desire to find non-overlapping
        matches no longer aids us in finding the single longest match.
        Where previously, we could use::

            >>> pst = PunktSentenceTokenizer()
            >>> text = "Very bad acting!!! I promise."
            >>> list(pst._lang_vars.period_context_re().finditer(text)) # doctest: +SKIP
            [<re.Match object; span=(9, 18), match='acting!!!'>]

        Now we have to find the word before (i.e. 'acting') separately, and `finditer`
        returns::

            >>> pst = PunktSentenceTokenizer()
            >>> text = "Very bad acting!!! I promise."
            >>> list(pst._lang_vars.period_context_re().finditer(text)) # doctest: +NORMALIZE_WHITESPACE
            [<re.Match object; span=(15, 16), match='!'>,
            <re.Match object; span=(16, 17), match='!'>,
            <re.Match object; span=(17, 18), match='!'>]

        So, we need to find the word before the match from right to left, and then manually remove
        the overlaps. That is what this method does::

            >>> pst = PunktSentenceTokenizer()
            >>> text = "Very bad acting!!! I promise."
            >>> list(pst._match_potential_end_contexts(text))
            [(<re.Match object; span=(17, 18), match='!'>, 'acting!!! I')]

        :param text: String of one or more sentences
        :type text: str
        :return: Generator of match-context tuples.
        :rtype: Iterator[Tuple[Match, str]]
        """
        previous_slice = slice(0, 0)
        previous_match = None
        for match in self._lang_vars.period_context_re().finditer(text):
            # Get the slice of the previous word
            before_text = text[previous_slice.stop : match.start()]
            index_after_last_space = self._get_last_whitespace_index(before_text)
            if index_after_last_space:
                # + 1 to exclude the space itself
                index_after_last_space += previous_slice.stop + 1
            else:
                index_after_last_space = previous_slice.start
            prev_word_slice = slice(index_after_last_space, match.start())

            # If the previous slice does not overlap with this slice, then
            # we can yield the previous match and slice. If there is an overlap,
            # then we do not yield the previous match and slice.
            if previous_match and previous_slice.stop <= prev_word_slice.start:
                yield (
                    previous_match,
                    text[previous_slice]
                    + previous_match.group()
                    + previous_match.group("after_tok"),
                )
            previous_match = match
            previous_slice = prev_word_slice

        # Yield the last match and context, if it exists
        if previous_match:
            yield (
                previous_match,
                text[previous_slice]
                + previous_match.group()
                + previous_match.group("after_tok"),
            )

    def _slices_from_text(self, text: str) -> Iterator[slice]:
        last_break = 0
        for match, context in self._match_potential_end_contexts(text):
            if self.text_contains_sentbreak(context):
                yield slice(last_break, match.end())
                if match.group("next_tok"):
                    # next sentence starts after whitespace
                    last_break = match.start("next_tok")
                else:
                    # next sentence starts at following punctuation
                    last_break = match.end()
        # The last sentence should not contain trailing whitespace.
        yield slice(last_break, len(text.rstrip()))

    def _realign_boundaries(
        self, text: str, slices: Iterator[slice]
    ) -> Iterator[slice]:
        """
        Attempts to realign punctuation that falls after the period but
        should otherwise be included in the same sentence.

        For example: "(Sent1.) Sent2." will otherwise be split as::

            ["(Sent1.", ") Sent1."].

        This method will produce::

            ["(Sent1.)", "Sent2."].
        """
        realign = 0
        for sentence1, sentence2 in _pair_iter(slices):
            sentence1 = slice(sentence1.start + realign, sentence1.stop)
            if not sentence2:
                if text[sentence1]:
                    yield sentence1
                continue

            m = self._lang_vars.re_boundary_realignment.match(text[sentence2])
            if m:
                yield slice(sentence1.start, sentence2.start + len(m.group(0).rstrip()))
                realign = m.end()
            else:
                realign = 0
                if text[sentence1]:
                    yield sentence1

    def text_contains_sentbreak(self, text: str) -> bool:
        """
        Returns True if the given text includes a sentence break.
        """
        found = False  # used to ignore last token
        for tok in self._annotate_tokens(self._tokenize_words(text)):
            if found:
                return True
            if tok.sentbreak:
                found = True
        return False

    def sentences_from_text_legacy(self, text: str) -> Iterator[str]:
        """
        Given a text, generates the sentences in that text. Annotates all
        tokens, rather than just those with possible sentence breaks. Should
        produce the same results as ``sentences_from_text``.
        """
        tokens = self._annotate_tokens(self._tokenize_words(text))
        return self._build_sentence_list(text, tokens)

    def sentences_from_tokens(
        self, tokens: Iterator[PunktToken]
    ) -> Iterator[PunktToken]:
        """
        Given a sequence of tokens, generates lists of tokens, each list
        corresponding to a sentence.
        """
        tokens = iter(self._annotate_tokens(self._Token(t) for t in tokens))
        sentence = []
        for aug_tok in tokens:
            sentence.append(aug_tok.tok)
            if aug_tok.sentbreak:
                yield sentence
                sentence = []
        if sentence:
            yield sentence

    def _annotate_tokens(self, tokens: Iterator[PunktToken]) -> Iterator[PunktToken]:
        """
        Given a set of tokens augmented with markers for line-start and
        paragraph-start, returns an iterator through those tokens with full
        annotation including predicted sentence breaks.
        """
        # Make a preliminary pass through the document, marking likely
        # sentence breaks, abbreviations, and ellipsis tokens.
        tokens = self._annotate_first_pass(tokens)

        # Make a second pass through the document, using token context
        # information to change our preliminary decisions about where
        # sentence breaks, abbreviations, and ellipsis occurs.
        tokens = self._annotate_second_pass(tokens)

        ## [XX] TESTING
        # tokens = list(tokens)
        # self.dump(tokens)

        return tokens

    def _build_sentence_list(
        self, text: str, tokens: Iterator[PunktToken]
    ) -> Iterator[str]:
        """
        Given the original text and the list of augmented word tokens,
        construct and return a tokenized list of sentence strings.
        """
        # Most of the work here is making sure that we put the right
        # pieces of whitespace back in all the right places.

        # Our position in the source text, used to keep track of which
        # whitespace to add:
        pos = 0

        # A regular expression that finds pieces of whitespace:
        white_space_regexp = re.compile(r"\s*")

        sentence = ""
        for aug_tok in tokens:
            tok = aug_tok.tok

            # Find the whitespace before this token, and update pos.
            white_space = white_space_regexp.match(text, pos).group()
            pos += len(white_space)

            # Some of the rules used by the punkt word tokenizer
            # strip whitespace out of the text, resulting in tokens
            # that contain whitespace in the source text.  If our
            # token doesn't match, see if adding whitespace helps.
            # If so, then use the version with whitespace.
            if text[pos : pos + len(tok)] != tok:
                pat = r"\s*".join(re.escape(c) for c in tok)
                m = re.compile(pat).match(text, pos)
                if m:
                    tok = m.group()

            # Move our position pointer to the end of the token.
            assert text[pos : pos + len(tok)] == tok
            pos += len(tok)

            # Add this token.  If it's not at the beginning of the
            # sentence, then include any whitespace that separated it
            # from the previous token.
            if sentence:
                sentence += white_space
            sentence += tok

            # If we're at a sentence break, then start a new sentence.
            if aug_tok.sentbreak:
                yield sentence
                sentence = ""

        # If the last sentence is empty, discard it.
        if sentence:
            yield sentence

    # [XX] TESTING
    def dump(self, tokens: Iterator[PunktToken]) -> None:
        print("writing to /tmp/punkt.new...")
        with open("/tmp/punkt.new", "w") as outfile:
            for aug_tok in tokens:
                if aug_tok.parastart:
                    outfile.write("\n\n")
                elif aug_tok.linestart:
                    outfile.write("\n")
                else:
                    outfile.write(" ")

                outfile.write(str(aug_tok))

    # ////////////////////////////////////////////////////////////
    # { Customization Variables
    # ////////////////////////////////////////////////////////////

    PUNCTUATION = tuple(";:,.!?")

    # ////////////////////////////////////////////////////////////
    # { Annotation Procedures
    # ////////////////////////////////////////////////////////////

    def _annotate_second_pass(
        self, tokens: Iterator[PunktToken]
    ) -> Iterator[PunktToken]:
        """
        Performs a token-based classification (section 4) over the given
        tokens, making use of the orthographic heuristic (4.1.1), collocation
        heuristic (4.1.2) and frequent sentence starter heuristic (4.1.3).
        """
        for token1, token2 in _pair_iter(tokens):
            self._second_pass_annotation(token1, token2)
            yield token1

    def _second_pass_annotation(
        self, aug_tok1: PunktToken, aug_tok2: PunktToken | None
    ) -> str | None:
        """
        Performs token-based classification over a pair of contiguous tokens
        updating the first.
        """
        # Is it the last token? We can't do anything then.
        if not aug_tok2:
            return

        if not aug_tok1.period_final:
            # We only care about words ending in periods.
            return
        typ = aug_tok1.type_no_period
        next_typ = aug_tok2.type_no_sentperiod
        tok_is_initial = aug_tok1.is_initial

        # [4.1.2. Collocation Heuristic] If there's a
        # collocation between the word before and after the
        # period, then label tok as an abbreviation and NOT
        # a sentence break. Note that collocations with
        # frequent sentence starters as their second word are
        # excluded in training.
        if (typ, next_typ) in self._params.collocations:
            aug_tok1.sentbreak = False
            aug_tok1.abbr = True
            return REASON_KNOWN_COLLOCATION

        # [4.2. Token-Based Reclassification of Abbreviations] If
        # the token is an abbreviation or an ellipsis, then decide
        # whether we should *also* classify it as a sentbreak.
        if (aug_tok1.abbr or aug_tok1.ellipsis) and (not tok_is_initial):
            # [4.1.1. Orthographic Heuristic] Check if there's
            # orthogrpahic evidence about whether the next word
            # starts a sentence or not.
            is_sent_starter = self._ortho_heuristic(aug_tok2)
            if is_sent_starter == True:  # noqa: E712
                aug_tok1.sentbreak = True
                return REASON_ABBR_WITH_ORTHOGRAPHIC_HEURISTIC

            # [4.1.3. Frequent Sentence Starter Heruistic] If the
            # next word is capitalized, and is a member of the
            # frequent-sentence-starters list, then label tok as a
            # sentence break.
            if aug_tok2.first_upper and next_typ in self._params.sent_starters:
                aug_tok1.sentbreak = True
                return REASON_ABBR_WITH_SENTENCE_STARTER

        # [4.3. Token-Based Detection of Initials and Ordinals]
        # Check if any initials or ordinals tokens that are marked
        # as sentbreaks should be reclassified as abbreviations.
        if tok_is_initial or typ == "##number##":
            # [4.1.1. Orthographic Heuristic] Check if there's
            # orthogrpahic evidence about whether the next word
            # starts a sentence or not.
            is_sent_starter = self._ortho_heuristic(aug_tok2)

            if is_sent_starter == False:  # noqa: E712
                aug_tok1.sentbreak = False
                aug_tok1.abbr = True
                if tok_is_initial:
                    return REASON_INITIAL_WITH_ORTHOGRAPHIC_HEURISTIC
                return REASON_NUMBER_WITH_ORTHOGRAPHIC_HEURISTIC

            # Special heuristic for initials: if orthogrpahic
            # heuristic is unknown, and next word is always
            # capitalized, then mark as abbrev (eg: J. Bach).
            if (
                is_sent_starter == "unknown"
                and tok_is_initial
                and aug_tok2.first_upper
                and not (self._params.ortho_context[next_typ] & _ORTHO_LC)
            ):
                aug_tok1.sentbreak = False
                aug_tok1.abbr = True
                return REASON_INITIAL_WITH_SPECIAL_ORTHOGRAPHIC_HEURISTIC

        return

    def _ortho_heuristic(self, aug_tok: PunktToken) -> bool | str:
        """
        Decide whether the given token is the first token in a sentence.
        """
        # Sentences don't start with punctuation marks:
        if aug_tok.tok in self.PUNCTUATION:
            return False

        ortho_context = self._params.ortho_context[aug_tok.type_no_sentperiod]

        # If the word is capitalized, occurs at least once with a
        # lower case first letter, and never occurs with an upper case
        # first letter sentence-internally, then it's a sentence starter.
        if (
            aug_tok.first_upper
            and (ortho_context & _ORTHO_LC)
            and not (ortho_context & _ORTHO_MID_UC)
        ):
            return True

        # If the word is lower case, and either (a) we've seen it used
        # with upper case, or (b) we've never seen it used
        # sentence-initially with lower case, then it's not a sentence
        # starter.
        if aug_tok.first_lower and (
            (ortho_context & _ORTHO_UC) or not (ortho_context & _ORTHO_BEG_LC)
        ):
            return False

        # Otherwise, we're not sure.
        return "unknown"




class PunktTokenizer(PunktSentenceTokenizer):
    """Punkt tokenizer whose parameters are read from a ``punkt_tab/<lang>`` directory."""

    def __init__(self, lang_dir):
        PunktSentenceTokenizer.__init__(self)
        self._params = load_punkt_params(lang_dir)


def load_punkt_params(lang_dir):
    """Same parsing as nltk.tokenize.punkt.load_punkt_params with nltk.tabdata.PunktDecoder."""
    from pathlib import Path

    lang_dir = Path(lang_dir)

    def _lines(name):
        with open(lang_dir / name, encoding="utf-8") as f:
            return [x[:-1] if x[-1] == "\n" else x for x in f]

    params = PunktParameters()
    params.collocations = {tuple(x.split("\t")) for x in _lines("collocations.tab")}
    params.sent_starters = set(_lines("sent_starters.txt"))
    params.abbrev_types = set(_lines("abbrev_types.txt"))
    params.ortho_context = defaultdict(
        int, {a: int(b) for a, b in (tuple(x.split("\t")) for x in _lines("ortho_context.tab"))}
    )
    return params
