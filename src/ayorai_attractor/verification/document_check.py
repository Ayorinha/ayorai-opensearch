"""Check claims, or an AI answer, against caller-supplied documents.

End-to-end, deterministic path that the HTTP API previously lacked: the caller sends
documents and either explicit claims or an answer to decompose; for each claim the
most relevant passages are selected lexically, the stance detector labels each
passage, and the deterministic Judge (ADR-002) returns the verdict. Every piece of
evidence carries its exact character offsets in the source document, and the response
carries the SHA-256 of each document and the version of each component, so the result
can be reproduced and audited.

Closed world: only the supplied documents are evidence. The claim text is never
derived from document content. Nothing is fetched from the network.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .claim_pipeline import ClaimVerificationPipeline
from .extraction import ExtractedClaim, RetrievedDocument, RuleClaimExtractor
from .models import Evidence, Stance, StanceEdge, Verdict
from .response import ResponsePolicy
from .stance import DetectedStance, RuleStanceDetector, StanceDetectionResult, StanceDetector

ENGINE_VERSION = "document-check-1"
MAX_PASSAGE_CHARS = 600
TOP_K_PASSAGES = 3
MIN_SUPPORT_COVERAGE = 0.8
_WORD_RE = re.compile(r"\w+", re.UNICODE)
_PARAGRAPH_RE = re.compile(r"\r?\n")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?;:])\s+")
_STOPWORDS = frozenset(
    """
    a o as os um uma uns umas de da do das dos em no na nos nas por para com sem sob
    que se e ou mas nao não ao aos à às pelo pela pelos pelas como mais menos foi ser
    sao são está esta este esse essa isso isto era eram tem têm ter seu sua seus suas
    the an of in on at to for with by from and or but not is are was were be been
    this that these those it its as into than then
    """.split()
)


class ConservativeStanceDetector:
    """Audit-grade wrapper: keeps every contradiction, demands near-complete support.

    The wrapped detector may label a passage as supporting on partial lexical overlap.
    For auditing, unsupported support is the costly error, so SUPPORTS is kept only if
    (a) at least MIN_SUPPORT_COVERAGE of the claim's content words occur in the passage
    and (b) every number in the claim occurs in the passage. Otherwise it becomes
    NEUTRAL (the claim then ends as unverified/abstention). CONTRADICTS is never
    weakened. The wrapped detector itself is not modified.
    """

    component = "stance_detector.conservative"

    def __init__(self, inner: StanceDetector | None = None) -> None:
        self.inner = inner or RuleStanceDetector()
        inner_name = getattr(self.inner, "component", type(self.inner).__name__)
        inner_version = getattr(self.inner, "version", "unknown")
        self.version = f"1(min_coverage={MIN_SUPPORT_COVERAGE};inner={inner_name}/{inner_version})"

    @staticmethod
    def support_is_complete(claim: str, passage: str) -> bool:
        claim_tokens = content_tokens(claim)
        passage_tokens = set(content_tokens(passage))
        numbers = {token for token in claim_tokens if token.isdigit()}
        if not numbers.issubset(passage_tokens):
            return False
        words = {token for token in claim_tokens if not token.isdigit()}
        if not words:
            return bool(numbers)
        return len(words & passage_tokens) / len(words) >= MIN_SUPPORT_COVERAGE

    def detect(
        self, claims: Sequence[ExtractedClaim], evidence: Sequence[Evidence]
    ) -> StanceDetectionResult:
        result = self.inner.detect(claims, evidence)
        claim_text = {item.claim.id: item.claim.text for item in claims}
        excerpt = {item.id: item.excerpt for item in evidence}
        adjusted = []
        for detected in result.edges:
            edge = detected.edge
            if edge.stance is Stance.SUPPORTS and not self.support_is_complete(
                claim_text[edge.claim_id], excerpt[edge.evidence_id]
            ):
                edge = StanceEdge(
                    id=edge.id,
                    claim_id=edge.claim_id,
                    evidence_id=edge.evidence_id,
                    stance=Stance.NEUTRAL,
                )
                detected = DetectedStance(edge, detected.confidence, detected.provenance)
            adjusted.append(detected)
        return StanceDetectionResult(tuple(adjusted))


@dataclass(frozen=True)
class CheckDocumentInput:
    id: str
    text: str
    source: str | None = None
    url: str | None = None
    media_type: str = "text/plain"
    page_starts: tuple[int, ...] = (0,)
    source_sha256: str | None = None

    def page_of(self, offset: int) -> int:
        page = 1
        for index, start in enumerate(self.page_starts, start=1):
            if offset >= start:
                page = index
            else:
                break
        return page


@dataclass(frozen=True)
class Passage:
    document_id: str
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class EvidenceView:
    document_id: str
    start: int
    end: int
    excerpt: str
    stance: str
    page: int = 1


@dataclass(frozen=True)
class ClaimCheck:
    claim_id: str
    claim: str
    status: str
    verdict: str | None
    confidence: float
    evidence: tuple[EvidenceView, ...]
    rationale: str
    abstention_reason: str | None = None


@dataclass(frozen=True)
class DocumentCheckResult:
    trace_id: str
    engine: dict[str, str]
    documents: tuple[dict[str, Any], ...]
    results: tuple[ClaimCheck, ...]
    summary: dict[str, int] = field(default_factory=dict)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def content_tokens(text: str) -> list[str]:
    """Accent- and case-insensitive content words, keeping numbers."""

    tokens = []
    for token in _WORD_RE.findall(_fold(text)):
        if token.isdigit() or (len(token) >= 3 and token not in _STOPWORDS):
            tokens.append(token)
    return tokens


def split_passages(document: CheckDocumentInput) -> list[Passage]:
    """Paragraphs, further split at sentence ends, with exact source offsets."""

    text = document.text
    passages: list[Passage] = []
    cursor = 0
    blocks: list[tuple[int, int]] = []
    for match in _PARAGRAPH_RE.finditer(text):
        blocks.append((cursor, match.start()))
        cursor = match.end()
    blocks.append((cursor, len(text)))
    for block_start, block_end in blocks:
        segment_start = block_start
        pieces: list[tuple[int, int]] = []
        for match in _SENTENCE_END_RE.finditer(text, block_start, block_end):
            pieces.append((segment_start, match.start()))
            segment_start = match.end()
        pieces.append((segment_start, block_end))
        current_start: int | None = None
        current_end = block_start
        for piece_start, piece_end in pieces:
            if piece_end <= piece_start:
                continue
            if current_start is None:
                current_start, current_end = piece_start, piece_end
            elif piece_end - current_start <= MAX_PASSAGE_CHARS:
                current_end = piece_end
            else:
                passages.append(_passage(document, current_start, current_end))
                current_start, current_end = piece_start, piece_end
        if current_start is not None:
            passages.append(_passage(document, current_start, current_end))
    return [item for item in passages if item.text.strip()]


def _passage(document: CheckDocumentInput, start: int, end: int) -> Passage:
    # Trim surrounding whitespace while keeping offsets exact.
    while start < end and document.text[start].isspace():
        start += 1
    while end > start and document.text[end - 1].isspace():
        end -= 1
    return Passage(document.id, start, end, document.text[start:end])


def rank_passages(claim: str, passages: Sequence[Passage], top_k: int) -> list[Passage]:
    """Deterministic lexical relevance; ties broken by document order."""

    claim_tokens = set(content_tokens(claim))
    if not claim_tokens:
        return []
    scored = []
    for order, passage in enumerate(passages):
        tokens = content_tokens(passage.text)
        if not tokens:
            continue
        shared = claim_tokens.intersection(tokens)
        if not shared:
            continue
        numeric = sum(1 for token in shared if token.isdigit())
        score = (len(shared) + numeric) / math.sqrt(len(set(tokens)))
        scored.append((-score, order, passage))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in scored[:top_k]]


def _trace_id(
    claims: Sequence[str], documents: Sequence[CheckDocumentInput], engine: dict[str, str]
) -> str:
    payload = {
        "claims": list(claims),
        "documents": [[doc.id, _sha256(doc.text)] for doc in documents],
        "engine": engine,
    }
    return "chk_" + _sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True))[:32]


def check_documents(
    documents: Sequence[CheckDocumentInput],
    *,
    claims: Sequence[str] | None = None,
    answer: str | None = None,
    stance_detector: StanceDetector | None = None,
    retrieved_at: datetime | None = None,
    top_k: int = TOP_K_PASSAGES,
) -> DocumentCheckResult:
    if (claims is None) == (answer is None):
        raise ValueError("provide exactly one of claims or answer")
    if not documents:
        raise ValueError("at least one document is required")
    if len({doc.id for doc in documents}) != len(documents):
        raise ValueError("document ids must be unique")

    detector = stance_detector or ConservativeStanceDetector()
    extractor = RuleClaimExtractor()
    if answer is not None:
        claim_texts = [item.claim.text for item in extractor.extract(answer).claims]
    else:
        claim_texts = [str(text).strip() for text in claims or () if str(text).strip()]
    engine = {
        "version": ENGINE_VERSION,
        "claim_extractor": (
            f"{extractor.component}/{extractor.version}" if answer is not None else "caller"
        ),
        "passage_selection": f"lexical-top{top_k}/max{MAX_PASSAGE_CHARS}",
        "stance_detector": (
            f"{getattr(detector, 'component', type(detector).__name__)}/"
            f"{getattr(detector, 'version', 'unknown')}"
        ),
        "judge": "ADR-002",
    }
    when = retrieved_at or datetime.now(UTC)
    passages = [passage for doc in documents for passage in split_passages(doc)]
    sources = {doc.id: doc.text for doc in documents}
    by_id = {doc.id: doc for doc in documents}
    origin = {doc.id: "sha256:" + _sha256(doc.text) for doc in documents}
    pipeline = ClaimVerificationPipeline(detector)

    results: list[ClaimCheck] = []
    for index, claim in enumerate(claim_texts, start=1):
        claim_id = f"clm_{index:03d}"
        selected = rank_passages(claim, passages, top_k)
        if not selected:
            results.append(
                ClaimCheck(
                    claim_id=claim_id,
                    claim=claim,
                    status=ResponsePolicy.ABSTAIN_NO_ANSWER.value,
                    verdict=None,
                    confidence=1.0,
                    evidence=(),
                    rationale="No passage of the supplied documents shares content with the claim.",
                    abstention_reason="no_relevant_passage",
                )
            )
            continue
        retrieved = [
            RetrievedDocument(
                id=f"{passage.document_id}#{passage.start}-{passage.end}",
                content=passage.text,
                source_id=passage.document_id,
                source_location=(
                    f"{by_id[passage.document_id].source or passage.document_id}"
                    f"#chars={passage.start}-{passage.end}"
                ),
                retrieved_at=when,
                start_offset=passage.start,
                end_offset=passage.end,
                canonical_url=by_id[passage.document_id].url,
                # One document = one origin: passages of the same document never count
                # as independent sources.
                origin_id=origin[passage.document_id],
            )
            for passage in selected
        ]
        outcome = pipeline.verify([claim], retrieved, sources=sources)
        stance_by_evidence = {edge.evidence_id: edge.stance.value for edge in outcome.stances}
        evidence = tuple(
            EvidenceView(
                document_id=item.source_id,
                start=item.start_offset,
                end=item.end_offset,
                excerpt=item.excerpt,
                stance=stance_by_evidence.get(item.id, "neutral"),
                page=by_id[item.source_id].page_of(item.start_offset),
            )
            for item in outcome.evidence
        )
        status = outcome.status.value
        verdict = outcome.verdict.value if isinstance(outcome.verdict, Verdict) else None
        if verdict == Verdict.UNVERIFIED.value:
            status = ResponsePolicy.ABSTAIN_NO_ANSWER.value
            verdict = None
        results.append(
            ClaimCheck(
                claim_id=claim_id,
                claim=claim,
                status=status,
                verdict=verdict,
                confidence=round(float(outcome.confidence), 6),
                evidence=evidence,
                rationale=outcome.rationale,
                abstention_reason=outcome.abstention_reason
                or ("insufficient_evidence" if verdict is None else None),
            )
        )

    summary: dict[str, int] = {}
    for item in results:
        key = item.verdict or item.status
        summary[key] = summary.get(key, 0) + 1
    return DocumentCheckResult(
        trace_id=_trace_id(claim_texts, documents, engine),
        engine=engine,
        documents=tuple(
            {
                "id": doc.id,
                "sha256": _sha256(doc.text),
                "characters": len(doc.text),
                "media_type": doc.media_type,
                "pages": len(doc.page_starts),
                "source_sha256": doc.source_sha256 or _sha256(doc.text),
            }
            for doc in documents
        ),
        results=tuple(results),
        summary=dict(sorted(summary.items())),
    )
