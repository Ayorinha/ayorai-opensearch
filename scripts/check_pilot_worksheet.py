#!/usr/bin/env python3
"""Offline structural check of a filled RGC pilot-02 worksheet.

Reads the Markdown worksheet filled by the human annotator
(``docs/eval/PILOT-RGC-02-WORKSHEET.md`` format) and checks each case against
the protocol rules that can be verified mechanically:

* the literal excerpt exists, byte for byte, in a captured official document
  (Amendment 1); a match found only after whitespace normalisation is reported
  as an error with a hint, because offsets would not reproduce;
* the reference label is one of the five RGC verdicts, or ``RULE_GAP`` (pilot
  only, Amendment 2 item 5);
* every ``REFUTED`` case quotes an incompatible sentence that exists literally
  in the excerpt or in the source document (Amendment 4 item 1);
* the ``rectified`` field agrees with the rectification answer (Amendment 4
  item 2);
* ``PARTIALLY_SUPPORTED`` cases are compound and list their atoms
  (Amendment 3); ``CONFLICTING`` cases name both sources and excerpts;
* the annotator confirmed the literal check against the source.

What this script deliberately does NOT do:

* it never runs the AYORAI ATTRACTOR, the stance detector or the Judge, and
  imports nothing from them, so no system output can reach the annotator;
* it never judges whether a label is correct, never suggests a label and
  never prints claims, excerpts or justifications - only case identifiers,
  field names and the rule that failed;
* it uses no network and no model.

Usage::

    python scripts/check_pilot_worksheet.py ficha-preenchida.md
    python scripts/check_pilot_worksheet.py ficha.md --documents outro.jsonl

Exit status: 0 when every filled case passes, 1 otherwise, 2 on bad input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ROOT / "evals" / "ptbr" / "sources" / "DOCUMENTS.jsonl"

LABELS = frozenset({"SUPPORTED", "REFUTED", "UNVERIFIED", "PARTIALLY_SUPPORTED", "CONFLICTING"})
PILOT_ONLY_LABELS = frozenset({"RULE_GAP"})

# Field prefixes as written in the worksheet, mapped to short keys.
FIELDS: tuple[tuple[str, str], ...] = (
    ("Identificador da fonte", "source_id"),
    ("Identificador", "case_id"),
    ("Afirmação redigida pelo anotador", "claim"),
    ("Fonte oficial (URL)", "source_url"),
    ("Órgão emissor e ato", "issuer"),
    ("Dispositivo exato", "provision"),
    ("Data de publicação", "dates"),
    ("Trecho literal exato", "excerpt"),
    ("Hash do artefato-fonte", "source_hash"),
    ("A fonte foi conferida literalmente?", "checked"),
    ("Há retificação aplicável?", "has_rectification"),
    ("Se sim, referência oficial da retificação", "rectification_ref"),
    ("Campo `rectified`", "rectified"),
    ("Afirmação simples ou composta?", "kind"),
    ("Se composta, transcrever os átomos", "atoms"),
    ("Rótulo de referência", "label"),
    ("Justificativa rastreável ao texto", "justification"),
    ("Se `REFUTED`, frase literal incompatível", "incompatible"),
    ("Se `CONFLICTING`, fonte primária A", "conflicting"),
    ("Tipo(s) de dificuldade", "difficulty"),
    ("Ambiguidade ou limitação identificada", "ambiguity"),
    ("Decisão final do anotador e motivo", "decision"),
)
CASE_HEADER = re.compile(r"^###\s+Caso\s+(\S+)\s*$")
TEMPLATE_PLACEHOLDERS = {"sim / não", "`true` / `false`"}


@dataclass
class Case:
    heading: str
    values: dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> str:
        value = self.values.get(key, "").strip()
        return "" if value.lower() in TEMPLATE_PLACEHOLDERS else value

    @property
    def name(self) -> str:
        return self.get("case_id") or f"Caso {self.heading}"

    def is_blank(self) -> bool:
        return not any(self.get(key) for _, key in FIELDS)


def _strip_quotes(value: str) -> str:
    value = value.strip()
    for left, right in (("“", "”"), ('"', '"'), ("«", "»"), ("`", "`")):
        if len(value) >= 2 and value.startswith(left) and value.endswith(right):
            return value[len(left) : -len(right)]
    return value


def _field_key(line: str) -> tuple[str, str] | None:
    text = line.lstrip()
    if not text.startswith("- "):
        return None
    body = text[2:]
    for prefix, key in FIELDS:
        if body.startswith(prefix):
            _, _, value = body.partition(":")
            return key, value.strip()
    return None


def parse_worksheet(text: str) -> list[Case]:
    """Split the worksheet into cases; continuation lines extend the last field."""
    cases: list[Case] = []
    current: Case | None = None
    last_key: str | None = None
    for line in text.splitlines():
        header = CASE_HEADER.match(line)
        if header:
            current = Case(header.group(1))
            cases.append(current)
            last_key = None
            continue
        if line.startswith("## ") or line.startswith("### "):
            current, last_key = None, None
            continue
        if current is None:
            continue
        parsed = _field_key(line)
        if parsed:
            last_key, value = parsed
            current.values[last_key] = value
        elif last_key and line.strip() and line.startswith((" ", "\t", ">")):
            joined = current.values[last_key] + "\n" + line.strip().lstrip(">").strip()
            current.values[last_key] = joined.strip()
    return cases


def load_documents(path: Path) -> dict[str, str]:
    documents: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row.get("source_id"), str) or not isinstance(row.get("text"), str):
            raise ValueError(f"{path}:{number}: source_id and text are required")
        documents[row["source_id"]] = row["text"]
    return documents


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _literal_locations(needle: str, documents: Mapping[str, str]) -> list[str]:
    return [source_id for source_id, text in documents.items() if needle in text]


def check_case(case: Case, documents: Mapping[str, str]) -> list[str]:
    problems: list[str] = []
    for key, label in (
        ("case_id", "Identificador"),
        ("source_id", "Identificador da fonte"),
        ("claim", "Afirmação"),
        ("source_url", "Fonte oficial (URL)"),
        ("excerpt", "Trecho literal exato"),
        ("label", "Rótulo de referência"),
        ("justification", "Justificativa"),
    ):
        if not case.get(key):
            problems.append(f"campo obrigatório vazio: {label}")

    excerpt = _strip_quotes(case.get("excerpt"))
    source_id = case.get("source_id").strip("` ")
    scope: Mapping[str, str] = {}
    if source_id and source_id in documents:
        scope = {source_id: documents[source_id]}
    elif source_id:
        problems.append(
            "a fonte indicada não está no corpus capturado; registrar a fonte (DEC-002) "
            "antes de usá-la"
        )
    if excerpt and source_id in documents:
        if not _literal_locations(excerpt, scope):
            if any(_normalise(excerpt) in _normalise(text) for text in scope.values()):
                problems.append(
                    "trecho só confere após normalizar espaços/quebras de linha; "
                    "transcreva exatamente como no artefato capturado (Emenda 1)"
                )
            else:
                problems.append("trecho não aparece literalmente na fonte declarada (Emenda 1)")

    if case.get("checked").lower() not in {"sim", "s"}:
        problems.append("a conferência literal da fonte não foi confirmada com 'Sim'")

    label = case.get("label").strip("` ").upper()
    if label and label not in LABELS | PILOT_ONLY_LABELS:
        problems.append("rótulo fora dos cinco vereditos do RGC (Emenda 2)")

    if label == "REFUTED":
        incompatible = _strip_quotes(case.get("incompatible"))
        if not incompatible:
            problems.append("REFUTED sem a frase literal incompatível (Emenda 4, item 1)")
        elif incompatible not in excerpt and not _literal_locations(incompatible, scope):
            problems.append(
                "a frase incompatível não aparece literalmente no trecho nem na fonte (Emenda 4)"
            )

    has_rectification = case.get("has_rectification").lower()
    rectified = case.get("rectified").strip("` ").lower()
    if rectified not in {"true", "false"}:
        problems.append("campo rectified deve ser true ou false (Emenda 4, item 2)")
    elif has_rectification in {"sim", "s"} and rectified != "true":
        problems.append("há retificação aplicável, mas rectified não é true")
    elif has_rectification in {"não", "nao", "n"} and rectified != "false":
        problems.append("não há retificação aplicável, mas rectified não é false")
    if rectified == "true" and not case.get("rectification_ref"):
        problems.append("rectified true sem referência oficial da retificação")

    kind = case.get("kind").lower()
    is_compound = kind.startswith("compost")
    if is_compound and not case.get("atoms"):
        problems.append("afirmação composta sem átomos e offsets (Emenda 3)")
    if label == "PARTIALLY_SUPPORTED" and not is_compound:
        problems.append("PARTIALLY_SUPPORTED exige afirmação composta com átomos (Emenda 3)")
    if label == "CONFLICTING" and not case.get("conflicting"):
        problems.append("CONFLICTING sem as duas fontes e os dois trechos")
    return problems


def check_worksheet(text: str, documents: Mapping[str, str]) -> dict[str, list[str]]:
    report: dict[str, list[str]] = {}
    seen: set[str] = set()
    for case in parse_worksheet(text):
        if case.is_blank():
            continue
        problems = check_case(case, documents)
        if case.name in seen:
            problems.append("identificador repetido")
        seen.add(case.name)
        report[case.name] = problems
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("worksheet", type=Path)
    parser.add_argument("--documents", type=Path, default=DOCUMENTS)
    args = parser.parse_args(argv)
    try:
        documents = load_documents(args.documents)
        report = check_worksheet(args.worksheet.read_text(encoding="utf-8"), documents)
    except (OSError, ValueError) as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2
    if not report:
        print("nenhum caso preenchido encontrado")
        return 1
    failed = 0
    for name, problems in report.items():
        if problems:
            failed += 1
            print(f"{name}:")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"{name}: ok")
    print(f"{len(report)} caso(s) preenchido(s); {failed} com pendências")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
