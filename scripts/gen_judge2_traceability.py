#!/usr/bin/env python3
"""Generate Judge 2 rule-to-test-to-Golden traceability from a checked mapping."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "judge2" / "TRACEABILITY.md"
GOLDENS = (ROOT / "evals/golden/v0-r2.jsonl", ROOT / "evals/golden/v0.1-r2.jsonl")

# Each normative rule must point to an existing executable test.
RULES: list[dict[str, Any]] = [
 {"id":"G1","meaning":"Entrada inválida; códigos G não podem gerar veredito.","tests":[("tests/verification/test_judge2_gates.py","test_t11_each_g1_code_has_a_specific_negative_case"),("tests/verification/test_judge2_canonical_output.py","test_t8_invariant_i1_holds_for_every_decision_state")],"selector":"none","note":"Sem caso Golden inválido; coberto por testes negativos dedicados."},
 {"id":"G2","meaning":"Abstenção sem veredito factual.","tests":[("tests/verification/test_judge2_gates.py","test_g2_returns_abstention_reason_without_verdict"),("tests/verification/test_judge2_canonical_output.py","test_t8_invariant_i1_holds_for_every_decision_state")],"selector":"abstained","note":""},
 {"id":"E1","meaning":"Offsets válidos, ordenados e dentro dos limites do documento.","tests":[("tests/verification/test_judge2_gates.py","test_t11_each_evidence_rejection_reason_is_recorded"),("tests/verification/test_judge2_gates.py","test_offsets_count_unicode_code_points_for_accented_source")],"selector":"none","note":"Golden r2 não armazena spans nem payloads brutos de evidência."},
 {"id":"E2","meaning":"Trecho consistente com a fonte e seu hash quando aplicável.","tests":[("tests/verification/test_judge2_gates.py","test_fabricated_excerpt_without_hash_is_rejected"),("tests/verification/test_judge2_gates.py","test_excerpt_shifted_by_one_character_is_rejected"),("tests/verification/test_judge2_gates.py","test_nfd_excerpt_matches_nfc_source_after_normalization")],"selector":"none","note":"Golden r2 não armazena payloads brutos ou hashes de trecho."},
 {"id":"E3","meaning":"Evidência só conta com aresta SUPPORTS/CONTRADICTS admissível.","tests":[("tests/verification/test_judge2_gates.py","test_valid_supporting_evidence_is_admitted_without_verdict"),("tests/verification/test_judge2_adjudication.py","test_only_gate_admitted_evidence_contributes_to_verdict")],"selector":"none","note":"Golden r2 não serializa arestas de stance nem evidência admitida."},
 {"id":"A1","meaning":"S=0 e C=0 → UNVERIFIED.","tests":[("tests/verification/test_judge2_adjudication.py","test_t1_atomic_truth_table_covers_support_zero_to_three_and_contradiction_zero_to_two")],"selector":"atomic:UNVERIFIED","note":""},
 {"id":"A2","meaning":"S≥1 e C=0 → SUPPORTED.","tests":[("tests/verification/test_judge2_adjudication.py","test_t1_atomic_truth_table_covers_support_zero_to_three_and_contradiction_zero_to_two")],"selector":"atomic:SUPPORTED","note":""},
 {"id":"A3","meaning":"S=0 e C≥1 → REFUTED.","tests":[("tests/verification/test_judge2_adjudication.py","test_t1_atomic_truth_table_covers_support_zero_to_three_and_contradiction_zero_to_two")],"selector":"atomic:REFUTED","note":""},
 {"id":"A4","meaning":"S≥1 e C≥1 → CONFLICTING.","tests":[("tests/verification/test_judge2_adjudication.py","test_t1_atomic_truth_table_covers_support_zero_to_three_and_contradiction_zero_to_two")],"selector":"atomic:CONFLICTING","note":""},
 {"id":"R0","meaning":"Nenhum cluster decisório admissível.","tests":[("tests/verification/test_judge2_adjudication.py","test_t1_provenance_selects_r2_or_r3_without_changing_verdict"),("tests/verification/test_judge2_adjudication.py","test_conflicting_atomic_decision_exposes_both_sides_and_uses_minimum")],"selector":"robustness:R0","note":""},
 {"id":"R1","meaning":"Um cluster decisório admissível.","tests":[("tests/verification/test_judge2_adjudication.py","test_t1_provenance_selects_r2_or_r3_without_changing_verdict"),("tests/verification/test_judge2_adjudication.py","test_composite_robustness_is_minimum_of_atoms_selected_by_rule")],"selector":"robustness:R1","note":""},
 {"id":"R2","meaning":"Dois ou mais clusters, independência não plenamente confirmada.","tests":[("tests/verification/test_judge2_adjudication.py","test_t1_provenance_selects_r2_or_r3_without_changing_verdict")],"selector":"robustness:R2","note":""},
 {"id":"R3","meaning":"Dois ou mais clusters com proveniência completa.","tests":[("tests/verification/test_judge2_adjudication.py","test_t1_provenance_selects_r2_or_r3_without_changing_verdict")],"selector":"robustness:R3","note":""},
 {"id":"K1","meaning":"Qualquer átomo REFUTED → composto REFUTED.","tests":[("tests/verification/test_judge2_adjudication.py","test_t2_composite_truth_table_exhaustive_for_multisets_up_to_four_atoms")],"selector":"composite:REFUTED","note":"Nenhum caso Golden composto atual exercita K1; tabela exaustiva cobre a regra."},
 {"id":"K2","meaning":"Sem K1, qualquer átomo CONFLICTING → composto CONFLICTING.","tests":[("tests/verification/test_judge2_adjudication.py","test_t2_composite_truth_table_exhaustive_for_multisets_up_to_four_atoms")],"selector":"composite:CONFLICTING","note":""},
 {"id":"K3","meaning":"Todos os átomos SUPPORTED → composto SUPPORTED.","tests":[("tests/verification/test_judge2_adjudication.py","test_t2_composite_truth_table_exhaustive_for_multisets_up_to_four_atoms")],"selector":"composite:SUPPORTED","note":""},
 {"id":"K4","meaning":"Sem K1–K3, algum átomo SUPPORTED → PARTIALLY_SUPPORTED.","tests":[("tests/verification/test_judge2_adjudication.py","test_t2_composite_truth_table_exhaustive_for_multisets_up_to_four_atoms")],"selector":"composite:PARTIALLY_SUPPORTED","note":"Nenhum caso Golden composto atual exercita K4; tabela exaustiva cobre a regra."},
 {"id":"K5","meaning":"Nenhum átomo decisório → UNVERIFIED.","tests":[("tests/verification/test_judge2_adjudication.py","test_t2_composite_truth_table_exhaustive_for_multisets_up_to_four_atoms")],"selector":"composite:UNVERIFIED","note":"Nenhum caso Golden composto atual exercita K5; tabela exaustiva cobre a regra."},
]
EXPECTED_IDS = ["G1","G2","E1","E2","E3","A1","A2","A3","A4","R0","R1","R2","R3","K1","K2","K3","K4","K5"]

def read_golden(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def case_matches(case: dict[str, Any], selector: str) -> bool:
    claims = case.get("expected_claims", [])
    if selector == "none": return False
    if selector == "abstained": return case.get("expected_decision_state") == "ABSTAINED"
    kind, value = selector.split(":", 1)
    if kind == "atomic": return any(claim.get("verdict") == value for claim in claims)
    if kind == "robustness": return case.get("expected_robustness") == value or any(claim.get("robustness") == value for claim in claims)
    if kind == "composite": return len(claims) > 1 and case.get("expected_verdict") == value
    raise ValueError(f"unknown Golden selector: {selector}")

def validate_mapping() -> None:
    ids = [rule["id"] for rule in RULES]
    if ids != EXPECTED_IDS or len(ids) != len(set(ids)):
        raise SystemExit("traceability rule IDs do not exactly match the normative rule set")
    missing = []
    for rule in RULES:
        if not rule["tests"]:
            missing.append(f"{rule['id']}: no test mapped")
            continue
        for test_path, test_name in rule["tests"]:
            path = ROOT / test_path
            pattern = rf"^\s*def\s+{re.escape(test_name)}\s*\("
            if not path.is_file() or not re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE):
                missing.append(f"{rule['id']}: missing {test_path}::{test_name}")
    if missing:
        raise SystemExit("traceability rules without executable tests:\n" + "\n".join(missing))

def render() -> str:
    validate_mapping()
    datasets = [(path.name, read_golden(path)) for path in GOLDENS]
    lines = [
        "# Judge 2.0.0 — Traceability (generated)", "",
        "Generated by python scripts/gen_judge2_traceability.py. Do not edit manually.", "",
        "Source: ADR-009 §§3–9. Test identifiers are checked against the test files; a rule without an existing test fails generation/check mode.", "",
        "| Rule | Normative behavior | Tests | Golden r2 cases |", "|---|---|---|---|",
    ]
    for rule in RULES:
        test_text = "<br>".join(f"{path}::{name}" for path, name in rule["tests"])
        golden_text = []
        for name, cases in datasets:
            ids = [str(case.get("id", "?")) for case in cases if case_matches(case, rule["selector"])]
            if ids: golden_text.append(f"{name}: {', '.join(ids)}")
        golden = "<br>".join(golden_text) if golden_text else (rule["note"] or "—")
        lines.append(f"| **{rule['id']}** | {rule['meaning']} | {test_text} | {golden} |")
    lines.extend([
        "", "## Coverage notes", "",
        "- Golden v0-r2 and v0.1-r2 have the same case IDs; each dataset is listed independently.",
        "- E1–E3 are tested at the evidence-gate layer; current Golden r2 records do not carry raw offsets, excerpts, hashes, or stance edges, so no direct Golden case is claimed for those rules.",
        "- G1 negative inputs and composite K1/K4/K5 are covered by dedicated negative tests or the exhaustive composite truth table where no direct Golden case exists.",
        "- This matrix records test-to-rule coverage; it does not claim that tests prove factual correctness outside the declared scope.", "",
    ])
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail unless committed document matches generated bytes")
    args = parser.parse_args()
    generated = render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != generated:
            print("docs/judge2/TRACEABILITY.md is stale; run python scripts/gen_judge2_traceability.py", file=sys.stderr)
            return 1
        print("Judge 2 traceability parity: OK")
        return 0
    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"generated {OUTPUT.relative_to(ROOT)} with {len(RULES)} rules")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
