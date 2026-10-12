from __future__ import annotations
import re
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
import pytest
from ayorai_attractor.verification.judge2 import adjudicate, verify_output
from ayorai_attractor.verification.judge2.explanations import explain_canonical_result
from ayorai_attractor.verification.models import Evidence

ROOT = Path(__file__).resolve().parents[2]
VERDICTS = {"SUPPORTED", "PARTIALLY_SUPPORTED", "REFUTED", "UNVERIFIED", "CONFLICTING"}

def request_one(*, out_of_scope: bool = False, invalid: bool = False) -> dict[str, object]:
    claim_text = "Claim A"
    evidence = Evidence(
        id="e1", claim_id="c1", source_id="source-e1",
        source_location="https://example.test/e1",
        retrieved_at=datetime(2026, 10, 11, tzinfo=UTC),
        start_offset=0, end_offset=1, excerpt="x", origin_id="origin-e1",
    )
    return {
        "protocol_version": "r2-a", "claim_id": "c1", "claim_text": claim_text,
        "atoms": [] if invalid else [{"id":"a1","text":claim_text,"start_offset":0,"end_offset":len(claim_text)}],
        "evidence": [] if invalid or out_of_scope else [evidence],
        "stances": [] if invalid or out_of_scope else [{"id":"st1","atom_id":"a1","evidence_id":"e1","stance":"SUPPORTS"}],
        "source_texts": {} if invalid or out_of_scope else {"source-e1":"x"},
        "out_of_scope": out_of_scope,
    }

@pytest.mark.parametrize(
    ("request", "expected_state"),
    [(request_one(), "DECIDED"), (request_one(out_of_scope=True), "ABSTAINED"), (request_one(invalid=True), "INVALID_INPUT")],
)
def test_explanations_are_derived_from_canonical_result_without_changing_it(
    request: dict[str, object], expected_state: str,
) -> None:
    result = adjudicate(request).to_dict()
    before = deepcopy(result)
    explanation = explain_canonical_result(result)
    assert result == before
    assert verify_output(result)
    assert explanation["technical_explanation"] == result
    assert len(explanation["simple_explanation"]) <= 5
    assert explanation["simple_explanation"]
    assert result["decision_state"] == expected_state
    if expected_state == "DECIDED":
        verdict = result["verdict"]
        assert verdict in VERDICTS
        assert f"Veredito determinístico: {verdict}." in explanation["simple_explanation"]
    else:
        assert result["verdict"] is None
        assert any("nenhum veredito factual" in line for line in explanation["simple_explanation"])
        text = " ".join(explanation["simple_explanation"])
        assert not any(re.search(rf"\b{verdict}\b", text) for verdict in VERDICTS)

def test_explanation_rejects_tampered_or_contradictory_canonical_result() -> None:
    canonical = adjudicate(request_one()).to_dict()
    tampered = deepcopy(canonical)
    tampered["verdict"] = "REFUTED" if canonical["verdict"] != "REFUTED" else "SUPPORTED"
    with pytest.raises(ValueError, match="invalid output_sha256"):
        explain_canonical_result(tampered)
    abstained = adjudicate(request_one(out_of_scope=True)).to_dict()
    abstained["verdict"] = "UNVERIFIED"
    with pytest.raises(ValueError, match="invalid output_sha256"):
        explain_canonical_result(abstained)

def test_traceability_document_is_generated_and_in_parity() -> None:
    script = ROOT / "scripts" / "gen_judge2_traceability.py"
    subprocess.run([sys.executable, str(script), "--check"], cwd=ROOT, check=True)

def test_traceability_generator_has_a_test_for_every_normative_rule() -> None:
    script = ROOT / "scripts" / "gen_judge2_traceability.py"
    completed = subprocess.run([sys.executable, str(script), "--check"], cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    document = (ROOT / "docs" / "judge2" / "TRACEABILITY.md").read_text(encoding="utf-8")
    for rule_id in ("G1","G2","E1","E2","E3","A1","A2","A3","A4","R0","R1","R2","R3","K1","K2","K3","K4","K5"):
        assert f"**{rule_id}**" in document
