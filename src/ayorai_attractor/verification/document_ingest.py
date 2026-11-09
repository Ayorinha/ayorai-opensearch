"""Turn uploaded documents into text with page boundaries for /v1/check.

Supported: plain text and PDFs with a text layer (via the optional ``pypdf``
dependency, ``pip install ayorai-attractor[documents]``). A PDF without extractable
text (a scanned image) is rejected with an explicit error instead of producing an
empty, misleading check; OCR is not supported yet.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import importlib
from dataclasses import dataclass
from io import BytesIO

MAX_DECODED_BYTES = 5 * 1024 * 1024
MAX_DOCUMENT_CHARS = 200_000
MAX_PDF_PAGES = 300
PAGE_SEPARATOR = "\n\n"
SUPPORTED_MEDIA_TYPES = ("text/plain", "application/pdf")


class DocumentIngestError(ValueError):
    """The document cannot be turned into checkable text."""


@dataclass(frozen=True)
class IngestedDocument:
    text: str
    media_type: str
    page_starts: tuple[int, ...]
    source_sha256: str

    def page_of(self, offset: int) -> int:
        """1-based page containing the character offset."""

        page = 1
        for index, start in enumerate(self.page_starts, start=1):
            if offset >= start:
                page = index
            else:
                break
        return page


def _normalise(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip("\n")


def decode_base64(content: str) -> bytes:
    try:
        data = base64.b64decode(content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise DocumentIngestError("content_base64 is not valid base64") from exc
    if not data:
        raise DocumentIngestError("the decoded document is empty")
    if len(data) > MAX_DECODED_BYTES:
        raise DocumentIngestError(f"the decoded document exceeds {MAX_DECODED_BYTES} bytes")
    return data


def extract_pdf(data: bytes) -> tuple[str, tuple[int, ...]]:
    try:
        pypdf = importlib.import_module("pypdf")
    except ImportError as exc:
        raise DocumentIngestError(
            "PDF support requires the optional dependency 'pypdf' "
            "(pip install ayorai-attractor[documents])"
        ) from exc
    if not data.startswith(b"%PDF-"):
        raise DocumentIngestError("the content is not a PDF file")
    try:
        reader = pypdf.PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise DocumentIngestError("encrypted PDFs are not supported")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise DocumentIngestError(f"the PDF has more than {MAX_PDF_PAGES} pages")
        page_texts: list[str] = []
        total_characters = 0
        for page in reader.pages:
            page_text = _normalise(page.extract_text() or "")
            total_characters += len(page_text) + (len(PAGE_SEPARATOR) if page_texts else 0)
            if total_characters > MAX_DOCUMENT_CHARS:
                raise DocumentIngestError(
                    f"extracted document text exceeds {MAX_DOCUMENT_CHARS} characters"
                )
            page_texts.append(page_text)
    except DocumentIngestError:
        raise
    except Exception as exc:  # malformed PDFs raise many pypdf-specific errors
        raise DocumentIngestError(f"the PDF could not be read ({type(exc).__name__})") from exc
    if not any(text.strip() for text in page_texts):
        raise DocumentIngestError(
            "the PDF has no extractable text (scanned image?); OCR is not supported yet"
        )
    starts: list[int] = []
    parts: list[str] = []
    cursor = 0
    for index, text in enumerate(page_texts):
        if index:
            parts.append(PAGE_SEPARATOR)
            cursor += len(PAGE_SEPARATOR)
        starts.append(cursor)
        parts.append(text)
        cursor += len(text)
    return "".join(parts), tuple(starts)


def ingest(
    *, text: str | None, content_base64: str | None, media_type: str | None
) -> IngestedDocument:
    if (text is None) == (content_base64 is None):
        raise DocumentIngestError("provide exactly one of 'text' or 'content_base64'")
    if text is not None:
        if media_type not in (None, "text/plain"):
            raise DocumentIngestError("'text' documents must use media_type text/plain")
        if len(text) > MAX_DOCUMENT_CHARS:
            raise DocumentIngestError(
                f"document text exceeds {MAX_DOCUMENT_CHARS} characters"
            )
        return IngestedDocument(
            text=text,
            media_type="text/plain",
            page_starts=(0,),
            source_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )
    data = decode_base64(content_base64 or "")
    digest = hashlib.sha256(data).hexdigest()
    if media_type == "application/pdf":
        extracted, starts = extract_pdf(data)
        return IngestedDocument(extracted, "application/pdf", starts, digest)
    if media_type == "text/plain":
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentIngestError("text/plain content must be UTF-8") from exc
        if len(decoded) > MAX_DOCUMENT_CHARS:
            raise DocumentIngestError(
                f"document text exceeds {MAX_DOCUMENT_CHARS} characters"
            )
        return IngestedDocument(decoded, "text/plain", (0,), digest)
    raise DocumentIngestError(f"unsupported media_type; use one of {SUPPORTED_MEDIA_TYPES}")
