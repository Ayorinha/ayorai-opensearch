"""Deterministic explanations derived only from a canonical Judge 2 result."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, TypedDict

from .adjudication import verify_output

_DECISION_STATES = {"DECIDED", "ABSTAINED", "INVALID_INPUT"}
_VERDICTS = {"SUPPORTED", "PARTIALLY_SUPPORTED", "REFUTED", "UNVERIFIED", "CONFLICTING"}


class ExplanationOutput(TypedDict):
    simple_explanation: list[str]
    technical_explanation: dict[str, object]


def explain_canonical_result(canonical_result: Mapping[str, Any]) -> ExplanationOutput:
    """Build display explanations without adjudicating or changing the result.

    The canonical result is the sole input. Its output digest is checked before
    formatting, and the technical explanation is a detached copy of that result.
    """
    if not verify_output(canonical_result):
        raise ValueError("canonical Judge 2 result has an invalid output_sha256")

    state = canonical_result.get("decision_state")
    verdict = canonical_result.get("verdict")
    if state not in _DECISION_STATES:
        raise ValueError("canonical Judge 2 result has an unknown decision_state")
    if state == "DECIDED":
        if verdict not in _VERDICTS:
            raise ValueError("DECIDED result must contain a factual Judge 2 verdict")
    elif verdict is not None:
        raise ValueError("ABSTAINED and INVALID_INPUT results must have verdict=null")

    reason_codes = canonical_result.get("reason_codes", [])
    reasons = ", ".join(str(item) for item in reason_codes) or "nenhum"
    output_sha = str(canonical_result["output_sha256"])
    rules_version = str(canonical_result["judge_rules_version"])
    rule_trace = canonical_result.get("rule_trace", [])
    rule_ids = [
        str(item["rule_id"])
        for item in rule_trace
        if isinstance(item, Mapping) and isinstance(item.get("rule_id"), str)
    ]

    if state == "DECIDED":
        simple = [
            "Estado: DECIDED.",
            f"Veredito determinístico: {verdict}.",
            f"Robustez registrada: {canonical_result.get('robustness')}.",
            f"Regras registradas: {', '.join(rule_ids) or 'nenhuma'}.",
            f"Hash de saída: {output_sha}.",
        ]
    else:
        simple = [
            f"Estado: {state}; nenhum veredito factual foi emitido.",
            f"Motivos registrados: {reasons}.",
            f"Versão das regras: {rules_version}.",
            f"Hash de saída: {output_sha}.",
        ]

    return {
        "simple_explanation": simple,
        "technical_explanation": deepcopy(dict(canonical_result)),
    }
