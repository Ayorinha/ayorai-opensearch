"""Guard approved RGC decisions against contradictory documentation drift."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "DECISIONS-PENDING.md"
PREREGISTRATION = ROOT / "docs" / "eval" / "PREREGISTRATION-RGC-v1.md"
PROTOCOL = ROOT / "docs" / "eval" / "PROTOCOL-GOLDEN-V1.md"
APPROVED = {17: 7, 18: 8, 19: 9, 20: 10}


def _approved_decisions(index: str) -> dict[int, int]:
    """Require the maintainer's dated Option A approval in the decision index."""
    approved: dict[int, int] = {}
    for decision, amendment in APPROVED.items():
        pattern = re.compile(
            rf"^\| DEC-{decision:03d} \|[^\n]*\|\s*Aprovada pelo mantenedor "
            rf"\(2026-10-21\); opção A\s*\|",
            re.MULTILINE,
        )
        if pattern.search(index):
            approved[decision] = amendment
    return approved


def _approved_amendment_exists(document: str, amendment: int, decision: int) -> bool:
    """Require a dated normative amendment heading, never a Proposta heading."""
    heading = re.compile(
        rf"^## Emenda {amendment} \(2026-10-21\)[^\n]*$",
        re.MULTILINE,
    )
    for match in heading.finditer(document):
        title = match.group(0)
        if "Proposta" in title:
            continue
        if f"DEC-{decision:03d}" in title and "aprovada" in title.lower():
            return True
    return False


def test_approved_index_decisions_have_normative_amendments_in_both_documents() -> None:
    index = INDEX.read_text(encoding="utf-8")
    preregistration = PREREGISTRATION.read_text(encoding="utf-8")
    protocol = PROTOCOL.read_text(encoding="utf-8")

    approved = _approved_decisions(index)
    assert approved == APPROVED, f"unexpected approved decision set: {approved}"

    problems: list[str] = []
    for decision, amendment in approved.items():
        for path, document in (
            (PREREGISTRATION, preregistration),
            (PROTOCOL, protocol),
        ):
            if not _approved_amendment_exists(document, amendment, decision):
                problems.append(
                    f"{path.relative_to(ROOT)}: DEC-{decision:03d} has no "
                    f"approved normative Emenda {amendment}"
                )
    assert not problems, "\n".join(problems)


def test_approved_decisions_do_not_retain_unmarked_vigente_pending_notes() -> None:
    index = INDEX.read_text(encoding="utf-8")
    approved_ids = {f"DEC-{decision:03d}" for decision in _approved_decisions(index)}
    for path in (PREREGISTRATION, PROTOCOL):
        lines = path.read_text(encoding="utf-8").splitlines()
        for position, line in enumerate(lines):
            if not ("vigente" in line.casefold() and "permanece pendente" in line.casefold()):
                continue
            if not any(decision in line for decision in approved_ids):
                continue
            next_nonempty = next(
                (candidate.strip() for candidate in lines[position + 1 :] if candidate.strip()),
                "",
            )
            assert "superada" in next_nonempty.casefold(), (
                f"{path.relative_to(ROOT)}:{position + 1}: contradictory pending note "
                "lacks an immediate superada note"
            )


def test_consolidated_reading_lists_every_approved_amendment() -> None:
    preregistration = PREREGISTRATION.read_text(encoding="utf-8")
    start = preregistration.find("**Leitura consolidada (2026-10-21)**")
    assert start >= 0, "missing consolidated reading block"
    end = preregistration.find("\n## 1.", start)
    assert end >= 0, "consolidated reading block must precede section 1"
    block = preregistration[start:end]
    for amendment in range(6, 11):
        assert re.search(rf"\[Emenda {amendment}\b", block), (
            f"consolidated reading omits Emenda {amendment}"
        )
