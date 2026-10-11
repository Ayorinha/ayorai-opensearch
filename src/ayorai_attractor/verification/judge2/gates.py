"""Pre-adjudication gates for Judge 2.0.0.

This module can reject invalid input, abstain, or mark evidence admissible.
It deliberately does not calculate or emit a factual verdict.
"""
from __future__ import annotations

import hashlib
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from ayorai_attractor.verification.judge import InvalidJudgeInput
from ayorai_attractor.verification.models import Evidence

SUPPORTED_PROTOCOL_VERSION = "r2-a"
DecisionState = Literal["INVALID_INPUT", "ABSTAINED"]


@dataclass(frozen=True)
class EvidenceDisposition:
    """Admission result for one evidence-to-atom relation."""

    evidence_id: str
    atom_id: str
    admitted: bool
    reason: str | None = None


@dataclass(frozen=True)
class GateResult:
    """Pre-adjudication result; intentionally contains no verdict field."""

    decision_state: DecisionState | None
    reason_codes: tuple[str, ...]
    admissible: bool
    evidence: tuple[EvidenceDisposition, ...]
    rules_sha256: str


def _invalid(code: str, field: str, message: str) -> InvalidJudgeInput:
    return InvalidJudgeInput(code, field, message)


def _require_mapping(
    value: object, field: str
) -> Mapping[str, object] | InvalidJudgeInput:
    if not isinstance(value, Mapping):
        return _invalid("SCHEMA_VIOLATION", field, f"{field} must be an object")
    if not all(isinstance(key, str) for key in value):
        return _invalid("SCHEMA_VIOLATION", field, f"{field} keys must be strings")
    return value


def _validate_g1(
    *,
    protocol_version: str,
    claim_id: str,
    claim_text: str,
    atoms: Sequence[Mapping[str, object]],
    evidence: Sequence[Evidence],
    stances: Sequence[Mapping[str, object]],
) -> InvalidJudgeInput | None:
    if protocol_version != SUPPORTED_PROTOCOL_VERSION:
        return _invalid(
            "UNSUPPORTED_PROTOCOL_VERSION",
            "protocol_version",
            f"unsupported protocol version: {protocol_version}",
        )
    if not isinstance(claim_text, str):
        return _invalid("SCHEMA_VIOLATION", "claim_text", "claim_text must be a string")
    if not claim_text.strip():
        return _invalid("EMPTY_CLAIM", "claim_text", "claim text must not be empty")
    if not isinstance(claim_id, str) or not claim_id:
        return _invalid("SCHEMA_VIOLATION", "claim_id", "claim_id must be a non-empty string")
    if not isinstance(atoms, Sequence) or isinstance(atoms, str | bytes):
        return _invalid("SCHEMA_VIOLATION", "atoms", "atoms must be a sequence")
    if not atoms:
        return _invalid("NO_ATOMS", "atoms", "at least one atom is required")
    if not isinstance(evidence, Sequence) or isinstance(evidence, str | bytes):
        return _invalid("SCHEMA_VIOLATION", "evidence", "evidence must be a sequence")
    if not isinstance(stances, Sequence) or isinstance(stances, str | bytes):
        return _invalid("SCHEMA_VIOLATION", "stances", "stances must be a sequence")

    atom_ids: list[str] = []
    for index, raw_atom in enumerate(atoms):
        atom = _require_mapping(raw_atom, f"atoms[{index}]")
        if isinstance(atom, InvalidJudgeInput):
            return atom
        atom_id = atom.get("id")
        text = atom.get("text")
        start = atom.get("start_offset")
        end = atom.get("end_offset")
        if not isinstance(atom_id, str) or not atom_id:
            return _invalid("SCHEMA_VIOLATION", f"atoms[{index}].id", "atom id is required")
        if not isinstance(text, str) or not text:
            return _invalid("SCHEMA_VIOLATION", f"atoms[{index}].text", "atom text is required")
        if not isinstance(start, int) or isinstance(start, bool):
            return _invalid(
                "SCHEMA_VIOLATION",
                f"atoms[{index}].start_offset",
                "start_offset must be an integer",
            )
        if not isinstance(end, int) or isinstance(end, bool):
            return _invalid(
                "SCHEMA_VIOLATION",
                f"atoms[{index}].end_offset",
                "end_offset must be an integer",
            )
        if start < 0 or end <= start or end > len(claim_text):
            return _invalid(
                "ATOM_SPAN_OUT_OF_RANGE",
                f"atoms[{index}]",
                "atom offsets must be ordered and within claim_text",
            )
        if claim_text[start:end] != text:
            return _invalid(
                "ATOM_SPAN_OUT_OF_RANGE",
                f"atoms[{index}]",
                "atom text must match claim_text at its declared offsets",
            )
        atom_ids.append(atom_id)
    if len(atom_ids) != len(set(atom_ids)):
        return _invalid("DUPLICATE_ID", "atoms", "atom ids must be unique")

    evidence_ids: list[str] = []
    for index, item in enumerate(evidence):
        if not isinstance(item, Evidence):
            return _invalid(
                "SCHEMA_VIOLATION",
                f"evidence[{index}]",
                "evidence entries must be validated Evidence objects",
            )
        if item.claim_id != claim_id:
            return _invalid(
                "DANGLING_REFERENCE",
                f"evidence[{index}].claim_id",
                "evidence must reference the evaluated claim",
            )
        evidence_ids.append(item.id)
    if len(evidence_ids) != len(set(evidence_ids)):
        return _invalid("DUPLICATE_ID", "evidence", "evidence ids must be unique")

    stance_ids: list[str] = []
    stance_pairs: list[tuple[str, str]] = []
    evidence_id_set = set(evidence_ids)
    atom_id_set = set(atom_ids)
    for index, raw_stance in enumerate(stances):
        stance = _require_mapping(raw_stance, f"stances[{index}]")
        if isinstance(stance, InvalidJudgeInput):
            return stance
        stance_id = stance.get("id")
        atom_id = stance.get("atom_id")
        evidence_id = stance.get("evidence_id")
        relation = stance.get("stance")
        if not isinstance(stance_id, str) or not stance_id:
            return _invalid("SCHEMA_VIOLATION", f"stances[{index}].id", "stance id is required")
        if not isinstance(atom_id, str) or not isinstance(evidence_id, str):
            return _invalid(
                "SCHEMA_VIOLATION",
                f"stances[{index}]",
                "atom_id and evidence_id are required",
            )
        if not isinstance(relation, str) or relation not in {
            "SUPPORTS", "CONTRADICTS", "NEUTRAL", "supports", "contradicts", "neutral"
        }:
            return _invalid(
                "SCHEMA_VIOLATION",
                f"stances[{index}].stance",
                "stance value is invalid",
            )
        stance_ids.append(stance_id)
        stance_pairs.append((atom_id, evidence_id))
        if atom_id not in atom_id_set or evidence_id not in evidence_id_set:
            return _invalid(
                "DANGLING_REFERENCE",
                f"stances[{index}]",
                "stance must reference an existing atom and evidence item",
            )
    if len(stance_ids) != len(set(stance_ids)):
        return _invalid("DUPLICATE_ID", "stances", "stance ids must be unique")
    if len(stance_pairs) != len(set(stance_pairs)):
        return _invalid(
            "DUPLICATE_STANCE",
            "stances",
            "only one stance is allowed for each atom/evidence pair",
        )
    return None


def _abstention_codes(
    *,
    out_of_scope: bool,
    factual_claim: bool,
    temporal_anchor_present: bool,
    retrieval_succeeded: bool,
    evidence_pool_integrity_ok: bool,
) -> tuple[str, ...]:
    codes: list[str] = []
    if out_of_scope:
        codes.append("OUT_OF_SCOPE")
    if not factual_claim:
        codes.append("NON_FACTUAL_CLAIM")
    if not temporal_anchor_present:
        codes.append("MISSING_TEMPORAL_ANCHOR")
    if not retrieval_succeeded:
        codes.append("RETRIEVAL_FAILURE")
    if not evidence_pool_integrity_ok:
        codes.append("EVIDENCE_POOL_INTEGRITY_FAILURE")
    return tuple(codes)


def _evidence_dispositions(
    atoms: Sequence[Mapping[str, object]],
    evidence: Sequence[Evidence],
    stances: Sequence[Mapping[str, object]],
    source_texts: Mapping[str, str],
) -> tuple[EvidenceDisposition, ...]:
    stance_by_pair: dict[tuple[str, str], str] = {}
    for raw_stance in stances:
        stance_by_pair[(str(raw_stance["atom_id"]), str(raw_stance["evidence_id"]))] = str(
            raw_stance["stance"]
        ).upper()

    results: list[EvidenceDisposition] = []
    for atom in atoms:
        atom_id = str(atom["id"])
        for item in evidence:
            source_text = source_texts.get(item.source_id)
            if not isinstance(source_text, str):
                results.append(EvidenceDisposition(item.id, atom_id, False, "SOURCE_UNAVAILABLE"))
                continue
            if (
                item.start_offset < 0
                or item.end_offset <= item.start_offset
                or item.end_offset > len(source_text)
            ):
                results.append(EvidenceDisposition(item.id, atom_id, False, "OFFSET_INVALID"))
                continue
            excerpt_at_offsets = unicodedata.normalize(
                "NFC", source_text[item.start_offset:item.end_offset]
            ) == unicodedata.normalize("NFC", item.excerpt)
            if not excerpt_at_offsets:
                results.append(EvidenceDisposition(item.id, atom_id, False, "EXCERPT_MISMATCH"))
                continue
            if item.normalized_content_hash is not None:
                normalized_source = unicodedata.normalize("NFC", source_text)
                actual_hash = hashlib.sha256(normalized_source.encode("utf-8")).hexdigest()
                if actual_hash != item.normalized_content_hash:
                    results.append(EvidenceDisposition(item.id, atom_id, False, "EXCERPT_MISMATCH"))
                    continue
            stance = stance_by_pair.get((atom_id, item.id))
            if stance not in {"SUPPORTS", "CONTRADICTS"}:
                results.append(EvidenceDisposition(item.id, atom_id, False, "NEUTRAL_STANCE"))
                continue
            results.append(EvidenceDisposition(item.id, atom_id, True))
    return tuple(results)


def evaluate_gates(
    *,
    protocol_version: str,
    claim_id: str,
    claim_text: str,
    atoms: Sequence[Mapping[str, object]],
    evidence: Sequence[Evidence],
    stances: Sequence[Mapping[str, object]],
    source_texts: Mapping[str, str],
    out_of_scope: bool = False,
    factual_claim: bool = True,
    temporal_anchor_present: bool = True,
    retrieval_succeeded: bool = True,
    evidence_pool_integrity_ok: bool = True,
) -> GateResult:
    """Evaluate G1/G2 and E1-E3 without producing any factual verdict.

    G1 failures reuse InvalidJudgeInput and become INVALID_INPUT. G2 reasons
    take precedence over evidence admission and become ABSTAINED. If neither
    gate rejects the request, E1-E3 classify each evidence/atom pair. The
    result has no verdict field by design.
    """
    from ayorai_attractor.verification.judge2 import load_rules

    _, contract_sha256 = load_rules()
    invalid_input = _validate_g1(
        protocol_version=protocol_version,
        claim_id=claim_id,
        claim_text=claim_text,
        atoms=atoms,
        evidence=evidence,
        stances=stances,
    )
    if isinstance(invalid_input, InvalidJudgeInput):
        return GateResult(
            decision_state="INVALID_INPUT",
            reason_codes=(invalid_input.code,),
            admissible=False,
            evidence=(),
            rules_sha256=contract_sha256,
        )

    abstention = _abstention_codes(
        out_of_scope=out_of_scope,
        factual_claim=factual_claim,
        temporal_anchor_present=temporal_anchor_present,
        retrieval_succeeded=retrieval_succeeded,
        evidence_pool_integrity_ok=evidence_pool_integrity_ok,
    )
    if abstention:
        return GateResult(
            decision_state="ABSTAINED",
            reason_codes=abstention,
            admissible=False,
            evidence=(),
            rules_sha256=contract_sha256,
        )

    dispositions = _evidence_dispositions(atoms, evidence, stances, source_texts)
    return GateResult(
        decision_state=None,
        reason_codes=(),
        admissible=True,
        evidence=dispositions,
        rules_sha256=contract_sha256,
    )


__all__ = [
    "EvidenceDisposition",
    "GateResult",
    "evaluate_gates",
]
