"""Guard approved RGC decisions against contradictory documentation drift."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "DECISIONS-PENDING.md"
PREREGISTRATION = ROOT / "docs" / "eval" / "PREREGISTRATION-RGC-v1.md"
PROTOCOL = ROOT / "docs" / "eval" / "PROTOCOL-GOLDEN-V1.md"

# Decisions that normatively define a numbered amendment in the RGC documents.
DECISION_AMENDMENTS = {
    "DEC-017": 7,
    "DEC-018": 8,
    "DEC-019": 9,
    "DEC-020": 10,
}


def _approved_amendment_exists(document: str, amendment: int, decision: str) -> bool:
    """Require a normative Emenda heading, never a Proposta heading."""
    pattern = rf"(?m)^## Emenda {amendment} \([^\n]*{re.escape(decision)}[^\n]*aprovad[^\n]*\)"
    return re.search(pattern, document, flags=re.IGNORECASE) is not None


def test_approved_index_decisions_have_normative_amendments_in_both_documents() -> None:
    index = INDEX.read_text(encoding="utf-8")
    preregistration = PREREGISTRATION.read_text(encoding="utf-8")
    protocol = PROTOCOL.read_text(encoding="utf-8")

    for decision, amendment in DECISION_AMENDMENTS.items():
        index_rows = [
            line for line in index.splitlines()
            if f"| {decision} |" in line and "Aprovada" in line
        ]
        if not index_rows:
            continue
        assert _approved_amendment_exists(preregistration, amendment, decision), (
            f"{decision} is approved in the index but Emenda {amendment} "
            "is missing or not normatively approved in the pre-registration"
        )
        assert _approved_amendment_exists(protocol, amendment, decision), (
            f"{decision} is approved in the index but Emenda {amendment} "
            "is missing or not normatively approved in the protocol"
        )


def test_approved_decisions_do_not_retain_unmarked_vigente_pending_notes() -> None:
    approved = {"DEC-017", "DEC-018", "DEC-019", "DEC-020"}
    for path in (PREREGISTRATION, PROTOCOL):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "vigente" not in line.casefold() or "permanece pendente" not in line.casefold():
                continue
            decisions = {decision for decision in approved if decision in line}
            for decision in decisions:
                next_nonblank = next(
                    (candidate.strip() for candidate in lines[index + 1 :] if candidate.strip()),
                    "",
                )
                assert "superada" in next_nonblank.casefold(), (
                    f"{path.relative_to(ROOT)}:{index + 1} marks {decision} "
                    "as vigente/pendente without an immediate superada note"
                )


def test_consolidated_reading_lists_every_approved_amendment() -> None:
    document = PREREGISTRATION.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^\*\*Leitura consolidada \(2026-10-21\)\*\*\s*(.*?)(?=^\*\*Registro histórico|^## )",
        document,
    )
    assert match is not None, "The consolidated reading block is missing"
    block = match.group(1)
    for amendment in range(6, 11):
        assert re.search(rf"\[Emenda {amendment}\b", block), (
            f"The consolidated reading block omits Emenda {amendment}"
        )
