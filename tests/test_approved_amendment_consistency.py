"""Keep approved DEC-017–020 amendments consistent across evaluation documents."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "docs" / "DECISIONS-PENDING.md"
PREREGISTRATION = ROOT / "docs" / "eval" / "PREREGISTRATION-RGC-v1.md"
PROTOCOL = ROOT / "docs" / "eval" / "PROTOCOL-GOLDEN-V1.md"
APPROVED = {17: 7, 18: 8, 19: 9, 20: 10}


def _approved_decisions(index: str) -> dict[int, int]:
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


def _has_approved_amendment(document: str, decision: int, amendment: int) -> bool:
    heading = re.compile(rf"^## Emenda {amendment} \(2026-10-21\)[^\n]*$", re.MULTILINE)
    for match in heading.finditer(document):
        title = match.group(0)
        if "Proposta" in title:
            continue
        if f"DEC-{decision:03d}" in title and "aprovada" in title.lower():
            return True
    return False


def test_approved_decisions_have_normative_amendments_in_both_documents() -> None:
    index = DECISIONS.read_text(encoding="utf-8")
    prereg = PREREGISTRATION.read_text(encoding="utf-8")
    protocol = PROTOCOL.read_text(encoding="utf-8")
    approved = _approved_decisions(index)
    assert approved == APPROVED

    problems: list[str] = []
    for decision, amendment in approved.items():
        for path, document in (
            (PREREGISTRATION, prereg),
            (PROTOCOL, protocol),
        ):
            if not _has_approved_amendment(document, decision, amendment):
                problems.append(
                    f"{path.relative_to(ROOT)}: DEC-{decision:03d} has no "
                    f"approved normative Emenda {amendment}"
                )
    assert not problems, "\n".join(problems)


def test_superseded_pending_notes_are_marked_immediately_afterward() -> None:
    index = DECISIONS.read_text(encoding="utf-8")
    approved_ids = {f"DEC-{decision:03d}" for decision in _approved_decisions(index)}
    problems: list[str] = []
    for path in (PREREGISTRATION, PROTOCOL):
        lines = path.read_text(encoding="utf-8").splitlines()
        for position, line in enumerate(lines):
            if not ("vigente" in line.lower() and "permanece pendente" in line.lower()):
                continue
            if not any(decision in line for decision in approved_ids):
                continue
            next_nonempty = next(
                (candidate.strip() for candidate in lines[position + 1 :] if candidate.strip()),
                "",
            )
            if "superada" not in next_nonempty.lower():
                problems.append(
                    f"{path.relative_to(ROOT)}:{position + 1}: "
                    "contradictory pending note lacks an immediate superseded note"
                )
    assert not problems, "\n".join(problems)


def test_consolidated_reading_lists_all_approved_amendments() -> None:
    prereg = PREREGISTRATION.read_text(encoding="utf-8")
    start = prereg.find("**Leitura consolidada (2026-10-21)**")
    assert start >= 0, "missing consolidated reading block"
    end = prereg.find("\n## 1.", start)
    assert end >= 0, "consolidated reading block must precede section 1"
    block = prereg[start:end]
    missing = [number for number in range(6, 11) if f"[Emenda {number}" not in block]
    assert not missing, f"consolidated reading omits approved amendments: {missing}"
