# ADR-009 — Deterministic adjudication contract and claim coverage

**Status:** Proposed / Draft — awaiting maintainer approval  
**Date:** 2026-10-10  
**Scope:** Proposed replacement for ADR-002 §§1 and 4, only after explicit maintainer approval  
**Normative status:** None yet. ADR-002 remains authoritative and unchanged until this ADR is accepted.

## Context

The project requires a deterministic, replayable adjudication boundary. Language models may extract claims, analyse passages, propose stance labels, or draft explanations, but they must not choose the final factual verdict. The adjudication contract must also make abstention, invalid input, claim coverage, robustness, rule identity, and replay provenance explicit.

This draft records the required decision points for review. It does not silently change the current Judge, frozen evaluation artifacts, thresholds, goldens, or accepted ADRs.

## Proposed decision-state contract

The proposed response decision states are:

- `DECIDED`: the deterministic Judge produced a verdict under a valid, versioned rule set.
- `ABSTAINED`: the request was understood but the system cannot responsibly adjudicate it under the contract.
- `INVALID_INPUT`: the input fails the declared structural or semantic input contract.

These are response decision states, not factual verdict labels. An abstention or invalid input must not be converted into a factual verdict.

## Proposed verdict boundary

The proposed verdict vocabulary excludes `VERIFIED`. A model-generated stance, confidence score, narrative explanation, operational success flag, or source count alone cannot authorize a factual verdict. The deterministic Judge is the only component permitted to emit the final verdict.

The exact replacement verdict set, aggregation precedence, and compatibility mapping must be confirmed by the maintainer before acceptance. Until then, the current ADR-002 rules remain in force.

## Robustness levels

The proposal requires four explicit robustness levels, `R0` through `R3`. Their exact acceptance criteria, failure behaviour, and mapping to tests must be copied from the authoritative Prompt Mestre v3 or supplied by the maintainer. This draft intentionally does not invent those definitions.

## G/E gates and A/K controls

The implementation and documentation must make the `G` and `E` gates and controls `A1`–`A4` and `K1`–`K5` explicit, versioned, testable, and traceable to their source requirements.

**Open requirement:** the full authoritative definitions and pass/fail criteria for these labels were not included in the material available for this draft. They must be transcribed and reviewed before this ADR can be accepted. No implementation may claim compliance based on labels alone.

## Atomic claims and coverage

The proposed contract requires:

1. Decompose compound assertions into atomic claims before adjudication.
2. Preserve the relationship between each atomic claim and the original assertion.
3. Report which parts of the original assertion are covered, unsupported, conflicting, abstained, or invalid under the accepted contract.
4. Prevent a verdict for one atomic claim from being silently generalized to uncovered parts of a compound assertion.
5. Make decomposition and coverage deterministic, versioned, and replayable wherever they affect the Judge's result.

The exact coverage formula and aggregation rule remain open until the authoritative Prompt Mestre v3 language is available.

## Rule identity, canonical serialization, and provenance

Every executable rule set must expose a stable `rule_id`, a rule version, and content hashes sufficient to identify the exact rules used for a decision. Structured inputs, intermediate adjudication records, and outputs must use a documented canonical JSON representation before hashing.

Canonicalization must specify UTF-8 encoding, key ordering, separators, Unicode handling, numeric representation, and treatment of absent versus null fields. Hashes identify content; they do not by themselves prove the truth of a claim.

Replay records must retain enough provenance to identify the rule version and the input/evidence references used, without storing secrets or unnecessary sensitive data.

## Frozen rules and migrations

- Existing rule-set 1.x behaviour remains frozen and executable as a historical reference.
- Any incompatible contract change must be introduced through a versioned migration, not an in-place reinterpretation of old records.
- Historical records must retain their original rule/replay identity and digests.
- Migration code must be idempotent, tested against temporary databases, and preserve legacy values and digests byte for byte.
- Frozen evaluation artifacts, manifests, goldens, thresholds, and reference hashes must not be regenerated or edited to make a new implementation pass.

## Derived goldens

Any golden set derived from a prior suite must have its own explicit manifest that records source suite/version, derivation method, rule version, source commit, hashes, and known limitations. Derived goldens must not silently replace their parent suite or be represented as independent confirmatory evidence when they are not independent.

A new or changed golden requires explicit maintainer approval before it is frozen or treated as normative.

## Required verification tests

Before acceptance, the implementation must provide tests for at least:

- atomic and compound assertions, including partial coverage;
- deterministic decomposition and stable claim-to-source mapping;
- all decision states, including invalid inputs that produce no factual verdict;
- all accepted verdict/aggregation combinations and boundary conditions;
- invariance to irrelevant ordering or formatting changes where the contract declares invariance;
- byte-for-byte deterministic canonical serialization and replay hashes;
- rule ID/version/hash consistency;
- migration idempotence and exact preservation of legacy values/digests;
- tampered or corrupted digests being detected rather than silently repaired;
- offline execution without external network dependencies;
- frozen artifact hashes remaining unchanged.

The final test matrix must map every accepted requirement to at least one test and, where applicable, a golden case.

## Explanations and limitations

The system should provide two explanation layers:

1. **Plain-language explanation:** no more than five lines, identifying the decision state, the result for the covered claim(s), the decisive evidence relationship, and any material limitation.
2. **Technical explanation:** rule IDs and versions, claim decomposition, evidence/provenance references, gate and robustness outcomes, canonical hashes, and reasons for abstention or invalid input.

Explanations are descriptive output, not an alternate decision channel. They must not upgrade a result or conceal uncovered claims, missing evidence, unresolved conflicts, or limitations.

## Compatibility and rollout

This ADR is a proposal only. Until the maintainer explicitly accepts it:

- ADR-002 §§1 and 4 remain authoritative;
- the current implementation and frozen goldens remain unchanged except through separately approved implementation PRs;
- no release, report, benchmark, or README may claim conformance to this proposed contract;
- unresolved definitions for R0–R3, G/E, A1–A4, K1–K5, verdict vocabulary, and coverage aggregation must be resolved before acceptance.

After approval, implementation should proceed in isolated pull requests with independent review of the exact head SHA, green CI, and unchanged frozen artifact hashes. No implementation PR may be merged merely because this draft exists.

## Approval

**Decision:** Pending maintainer review.  
**Supersedes:** Intended to replace ADR-002 §§1 and 4 only after explicit approval and a separately reviewed acceptance change.  
**Current authority:** ADR-002 remains in force.
