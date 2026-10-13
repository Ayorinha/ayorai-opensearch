"""Derive plain text from captured official PDFs, deterministically.

For each verified PDF source in evals/ptbr/SOURCES-REGISTRY.json this script
runs ``pdftotext`` (poppler) without layout mode, stores the exact output as a
derived text file and records its SHA-256 next to the original artifact hash.
It also builds evals/ptbr/sources/DOCUMENTS.jsonl, the full-text document file
required by PROTOCOL-GOLDEN-V1 (Emenda 1). No normalization is applied.

Usage:
    python scripts/extract_source_text.py           # write files and registry
    python scripts/extract_source_text.py --check   # verify hashes only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "evals" / "ptbr" / "SOURCES-REGISTRY.json"
DERIVED_DIR = ROOT / "evals" / "ptbr" / "sources" / "derived"
DOCUMENTS = ROOT / "evals" / "ptbr" / "sources" / "DOCUMENTS.jsonl"
LICENSE = "Ato oficial; sem proteção autoral (Lei nº 9.610/1998, art. 8º, IV) — DEC-002"

# Documents assembled from per-page sources, in reading order.
DOCUMENT_GROUPS = {
    "rgc-res-765-2023-dou-2023-11-10": {
        "title": "Resolução Anatel nº 765/2023 e Anexo (RGC) — DOU 10/11/2023, Seção 1, pp. 14-23",
        "pages": [f"anatel-res-765-2023-dou-2023-11-10-p{p}" for p in range(14, 24)],
    },
    "rgc-res-765-2023-retificacao-2023-12-26": {
        "title": "Retificação da Resolução Anatel nº 765/2023 — DOU de 26/12/2023, Seção 1, p. 13",
        "pages": ["anatel-res-765-2023-dou-2023-12-26-p13-retificacao"],
    },
    "rgc-res-765-2023-retificacao-2024-01-12": {
        "title": "Retificação da Resolução Anatel nº 765/2023 — DOU de 12/01/2024, Seção 1, p. 4",
        "pages": ["anatel-res-765-2023-dou-2024-01-12-p4-retificacao"],
    },
}


def _poppler_version() -> str:
    out = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True, check=False)
    return (out.stderr or out.stdout).splitlines()[0].strip()


def _extract(pdf: Path) -> bytes:
    result = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, check=True
    )
    return result.stdout


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify without writing")
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    by_id = {s["source_id"]: s for s in registry["sources"]}
    version = _poppler_version()
    problems: list[str] = []
    texts: dict[str, str] = {}

    for source in registry["sources"]:
        if source["status"] != "verified" or source["content_type"] != "application/pdf":
            continue
        pdf = ROOT / source["artifact_path"]
        if _sha256(pdf.read_bytes()) != source["sha256"]:
            problems.append(f"{source['source_id']}: original PDF hash mismatch")
            continue
        derived = _extract(pdf)
        digest = _sha256(derived)
        target = DERIVED_DIR / f"{source['source_id']}.txt"
        texts[source["source_id"]] = derived.decode("utf-8")
        if args.check:
            if source.get("derived_text_sha256") != digest:
                problems.append(f"{source['source_id']}: derived text hash differs ({version})")
            elif not target.is_file() or _sha256(target.read_bytes()) != digest:
                problems.append(f"{source['source_id']}: derived file missing or altered")
        else:
            DERIVED_DIR.mkdir(parents=True, exist_ok=True)
            target.write_bytes(derived)
            source["derived_text_present"] = True
            source["derived_text_sha256"] = digest

    lines = []
    for doc_id, group in DOCUMENT_GROUPS.items():
        pages = [by_id[p] for p in group["pages"]]
        text = "".join(texts[p["source_id"]] for p in pages)
        lines.append(
            json.dumps(
                {
                    "source_id": doc_id,
                    "title": group["title"],
                    "source_url": pages[0]["url"],
                    "page_source_ids": group["pages"],
                    "source_license": LICENSE,
                    "retrieved_at": pages[0]["retrieved_at"],
                    "extraction": f"pdftotext -enc UTF-8 (no layout); {version}",
                    "text_sha256": _sha256(text.encode("utf-8")),
                    "text": text,
                },
                ensure_ascii=False,
            )
        )
    documents = ("\n".join(lines) + "\n").encode("utf-8")

    if args.check:
        if not DOCUMENTS.is_file() or DOCUMENTS.read_bytes() != documents:
            problems.append("DOCUMENTS.jsonl differs from a fresh extraction")
    else:
        DOCUMENTS.write_bytes(documents)
        REGISTRY.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    for problem in problems:
        print("ERROR:", problem)
    print(f"{version}; {len(texts)} PDF sources processed; problems={len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
