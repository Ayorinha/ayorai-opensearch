"""Pilot-02 worksheet checker — synthetic worksheets and documents only."""

from __future__ import annotations

import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_pilot_worksheet.py"
CHECKER = runpy.run_path(str(SCRIPT))

DOC_TEXT = (
    "Art. 1º A Operadora Fictícia deverá responder em até 5 (cinco) dias úteis.\n"
    "Art. 2º O atendimento sintético funcionará 24 horas por dia.\n"
)
DOCS = {"sint-1": DOC_TEXT}


def _case(number: str = "01", **overrides: str) -> str:
    values = {
        "Identificador": f"p2-{number}",
        "Afirmação redigida pelo anotador": "Afirmação sintética.",
        "Fonte oficial (URL)": "https://example.test/sint-1",
        "Identificador da fonte / caminho do artefato capturado": "sint-1",
        "Trecho literal exato": "“Art. 2º O atendimento sintético funcionará 24 horas por dia.”",
        "A fonte foi conferida literalmente? Sim / Não": "Sim",
        "Há retificação aplicável? Sim / Não": "Não",
        "Se sim, referência oficial da retificação e dispositivo vigente": "",
        "Campo `rectified`: `true` / `false`": "false",
        "Afirmação simples ou composta?": "simples",
        "Se composta, transcrever os átomos": "",
        "Rótulo de referência": "SUPPORTED",
        "Justificativa rastreável ao texto": "Justificativa sintética.",
        "Se `REFUTED`, frase literal incompatível que demonstra a contradição": "",
        "Se `CONFLICTING`, fonte primária A, trecho A, fonte primária B e trecho B": "",
    }
    values.update(overrides)
    lines = [f"### Caso {number}", ""]
    for key, value in values.items():
        prefix = key.split(" Sim / Não")[0] if "Sim / Não" in key else key
        if prefix.startswith("Campo `rectified`"):
            prefix = "Campo `rectified`"
        lines.append(f"- {prefix}: {value}".rstrip())
    return "\n".join(lines) + "\n"


def _check(*cases: str) -> dict[str, list[str]]:
    return CHECKER["check_worksheet"]("\n".join(cases), DOCS)


def test_valid_case_passes() -> None:
    assert _check(_case()) == {"p2-01": []}


def test_source_identifier_is_required() -> None:
    report = _check(_case(**{"Identificador da fonte / caminho do artefato capturado": ""}))
    assert any("Identificador da fonte" in problem for problem in report["p2-01"])


def test_excerpt_must_match_the_declared_source() -> None:
    other_source_docs = {
        "sint-1": DOC_TEXT,
        "sint-2": DOC_TEXT,
    }
    worksheet = _case(**{"Identificador da fonte / caminho do artefato capturado": "sint-missing"})
    report = CHECKER["check_worksheet"](worksheet, other_source_docs)
    assert any("fonte indicada não está no corpus" in problem for problem in report["p2-01"])


def test_excerpt_from_another_source_is_rejected() -> None:
    documents = {
        "sint-1": DOC_TEXT,
        "sint-2": "Art. 9º Texto diferente e sintético.\\n",
    }
    worksheet = _case(**{"Identificador da fonte / caminho do artefato capturado": "sint-2"})
    report = CHECKER["check_worksheet"](worksheet, documents)
    assert any("não aparece literalmente na fonte declarada" in p for p in report["p2-01"])


def test_blank_template_has_no_filled_case() -> None:
    template = (ROOT / "docs" / "eval" / "PILOT-RGC-02-WORKSHEET.md").read_text(encoding="utf-8")
    assert CHECKER["check_worksheet"](template, DOCS) == {}


def test_excerpt_must_be_literal() -> None:
    report = _check(_case(**{"Trecho literal exato": "O atendimento funcionará sempre."}))
    assert any("não aparece literalmente" in p for p in report["p2-01"])


def test_whitespace_only_match_is_rejected_with_hint() -> None:
    excerpt = "Art. 2º O  atendimento sintético\nfuncionará 24 horas por dia."
    report = _check(_case(**{"Trecho literal exato": excerpt}))
    assert any("normalizar espaços" in p for p in report["p2-01"])


def test_refuted_requires_literal_incompatible_sentence() -> None:
    missing = _check(_case(**{"Rótulo de referência": "REFUTED"}))
    assert any("frase literal incompatível" in p for p in missing["p2-01"])
    invented = _check(
        _case(
            **{
                "Rótulo de referência": "REFUTED",
                "Se `REFUTED`, frase literal incompatível que demonstra a contradição": (
                    "“funcionará somente em dias úteis”"
                ),
            }
        )
    )
    assert any("não aparece literalmente" in p for p in invented["p2-01"])
    ok = _check(
        _case(
            **{
                "Rótulo de referência": "REFUTED",
                "Se `REFUTED`, frase literal incompatível que demonstra a contradição": (
                    "“funcionará 24 horas por dia”"
                ),
            }
        )
    )
    assert ok == {"p2-01": []}


def test_rectified_must_agree_with_rectification_answer() -> None:
    report = _check(
        _case(**{"Há retificação aplicável? Sim / Não": "Sim", "Campo `rectified`": "false"})
    )
    assert any("rectified não é true" in p for p in report["p2-01"])
    report = _check(
        _case(**{"Há retificação aplicável? Sim / Não": "Sim"}).replace(
            "Campo `rectified`: false", "Campo `rectified`: true"
        )
    )
    assert any("sem referência oficial" in p for p in report["p2-01"])


def test_partially_supported_requires_compound_claim_with_atoms() -> None:
    report = _check(_case(**{"Rótulo de referência": "PARTIALLY_SUPPORTED"}))
    assert any("exige afirmação composta" in p for p in report["p2-01"])
    compound = _check(
        _case(
            **{
                "Rótulo de referência": "PARTIALLY_SUPPORTED",
                "Afirmação simples ou composta?": "composta",
            }
        )
    )
    assert any("sem átomos" in p for p in compound["p2-01"])


def test_labels_outside_rgc_vocabulary_are_rejected() -> None:
    report = _check(_case(**{"Rótulo de referência": "VERIFIED"}))
    assert any("fora dos cinco vereditos" in p for p in report["p2-01"])
    assert _check(_case(**{"Rótulo de referência": "RULE_GAP"})) == {"p2-01": []}


def test_duplicate_identifiers_are_reported() -> None:
    report = _check(_case("01"), _case("02", Identificador="p2-01"))
    assert report["p2-01"] == ["identificador repetido"]


def test_output_never_contains_case_content(tmp_path: Path, capsys: object) -> None:
    documents = tmp_path / "docs.jsonl"
    documents.write_text(json.dumps({"source_id": "sint-1", "text": DOC_TEXT}) + "\n")
    worksheet = tmp_path / "ficha.md"
    worksheet.write_text(_case(**{"Trecho literal exato": "Trecho inexistente secreto."}))
    code = CHECKER["main"]([str(worksheet), "--documents", str(documents)])
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert code == 1
    assert "secreto" not in out and "Afirmação sintética" not in out


def test_checker_never_imports_the_system() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ayorai_attractor" not in source.replace("AYORAI ATTRACTOR", "")
    assert "import requests" not in source and "urllib" not in source
