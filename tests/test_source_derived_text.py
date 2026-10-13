"""Integrity of derived source text and of the benchmark document file."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "evals" / "ptbr" / "SOURCES-REGISTRY.json"
DERIVED_DIR = ROOT / "evals" / "ptbr" / "sources" / "derived"
DOCUMENTS = ROOT / "evals" / "ptbr" / "sources" / "DOCUMENTS.jsonl"


def _sources_with_text() -> list[dict[str, object]]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return [s for s in registry["sources"] if s["derived_text_present"]]


def test_derived_text_files_match_registry_hashes() -> None:
    sources = _sources_with_text()
    assert len(sources) == 12
    for source in sources:
        data = (DERIVED_DIR / f"{source['source_id']}.txt").read_bytes()
        assert hashlib.sha256(data).hexdigest() == source["derived_text_sha256"]


def test_documents_are_exact_concatenation_of_derived_pages() -> None:
    lines = DOCUMENTS.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    for line in lines:
        document = json.loads(line)
        expected = "".join(
            (DERIVED_DIR / f"{page}.txt").read_text(encoding="utf-8")
            for page in document["page_source_ids"]
        )
        assert document["text"] == expected
        assert hashlib.sha256(expected.encode("utf-8")).hexdigest() == document["text_sha256"]


def test_rgc_document_spans_resolution_and_full_annex() -> None:
    first = json.loads(DOCUMENTS.read_text(encoding="utf-8").splitlines()[0])
    text = first["text"]
    assert "RESOLUÇÃO ANATEL Nº 765, DE 6 DE NOVEMBRO DE 2023" in text
    assert "REGULAMENTO GERAL DE DIREITOS DO CONSUMIDOR DE SERVIÇOS DE TELECOMUNICAÇÕES" in text
    assert "Art. 101." in text


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="poppler pdftotext not installed")
def test_extraction_is_reproducible_with_same_poppler_version() -> None:
    version = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True, check=False)
    if "24.02.0" not in (version.stderr or version.stdout):
        pytest.skip("derived text was produced with poppler 24.02.0")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "extract_source_text.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
