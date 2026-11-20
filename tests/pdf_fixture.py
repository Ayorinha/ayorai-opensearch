"""Tiny hand-built PDFs (WinAnsi Helvetica text) for tests; no external generator."""

from __future__ import annotations


def make_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    contents = []
    for lines in pages:
        shown = b" ".join(
            b"("
            + line.encode("cp1252")
            .replace(b"\\", b"\\\\")
            .replace(b"(", b"\\(")
            .replace(b")", b"\\)")
            + b") Tj T*"
            for line in lines
        )
        stream = b"BT /F1 12 Tf 72 720 Td 14 TL " + shown + b" ET"
        contents.append(add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"))
    pages_id = len(objects) + len(contents) + 1
    page_ids = [
        add(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (pages_id, font, content)
        )
        for content in contents
    ]
    kids = b" ".join(b"%d 0 R" % page for page in page_ids)
    add(b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>" % len(page_ids))
    catalog = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        catalog,
        xref,
    )
    return out
