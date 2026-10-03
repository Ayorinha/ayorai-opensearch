# ADR-005 — Hybrid Multilingual Stance Detection

- **Status:** Accepted for architecture; NLI model selection is gated
- **Date:** 2026-10-03
- **Scope:** F1 multilingual stance evidence
- **Decision:** The stance layer is hybrid. Deterministic rules for numbers, dates, units and negation have priority when they fire. A three-class NLI backend handles the remaining claim/evidence pairs. Neither path may select the final verification verdict.

## Context

F0 exposed a cross-lingual failure mode: Golden claims are predominantly Portuguese while relevant corpus evidence is English. The existing lexical rule detector depends on token overlap and therefore produces excessive `NEUTRAL` edges for valid cross-language entailment.

ATTRACTOR needs a stance signal that can compare PT claim → EN evidence, PT → PT, EN → EN, and EN → PT where the selected model supports it.

The stance result is evidence for the deterministic ADR-002 Judge. It is not itself a verification verdict.

## Decision

### 1. Hybrid precedence

For each claim/evidence pair:

1. Parse deterministic numeric facts.
2. Compare dates at the granularity actually expressed.
3. Compare units and unit-bearing quantities.
4. Detect explicit negation in the supported PT/EN lexicon.
5. If a deterministic contradiction is established, emit `CONTRADICTS`.
6. If a deterministic equality/support condition is established, emit `SUPPORTS`.
7. Otherwise, delegate to the configured three-class NLI backend.
8. Preserve the backend's `SUPPORTS`, `CONTRADICTS` or `NEUTRAL` output as a stance edge with provenance.

A deterministic rule firing therefore outranks model inference for the rule domain. NLI is not allowed to override a triggered hard rule.

### 2. Judge boundary

The NLI backend and deterministic rules produce only stance edges and component provenance. They do not select a final verdict, aggregate clusters, decide provenance completeness, or change the caller-supplied claim. ADR-002 remains the sole authority for the final verdict.

### 3. Provenance

Every emitted stance edge must record component name, model/backend identifier, backend version, input SHA-256 over the claim/evidence pair, and output SHA-256 over the deterministic or model result. The NLI backend must be deterministic under a fixed model revision and inference configuration; random sampling is prohibited.

## NLI dependency boundary

The optional `[nli]` extra may provide `transformers` and CPU `torch`. Importing the base package must not require either dependency.

The backend interface is intentionally narrow: `classify(claim_text, evidence_text) -> {stance, confidence}`. The implementation must validate the model's label mapping explicitly. No positional assumption about `0/1/2` is permitted without reading and validating `id2label`.

## Model and training-data license gate

The initially proposed `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` declares **MIT** for its model repository, but its model card lists multiple training datasets, including XNLI, MultiNLI and ANLI. The model therefore cannot be approved for ATTRACTOR's strict commercial-use gate merely from the model's MIT declaration.

Public documentation reports non-commercial restrictions around XNLI, while MultiNLI contains source material under multiple licenses, including CC-BY-SA 3.0. ATTRACTOR therefore does not treat the proposed checkpoint as cleared solely because its model card says MIT.

A candidate model is admissible only when all of the following are documented: exact immutable model revision; exact model license; exact training datasets and immutable revisions; exact dataset licenses; commercial use permitted by those licenses; and compatibility with ATTRACTOR's Apache-2.0 distribution policy.

Until those conditions are evidenced, the candidate is **not approved** for the default F1 backend. A commercially clean candidate may be introduced in a later commit with its complete license/provenance record. The architecture does not hard-code the rejected checkpoint.

## Consequences

- Cross-language stance is no longer coupled to lexical token overlap.
- Safety-critical numeric/date/unit/negation conflicts remain deterministic and auditable.
- NLI uncertainty remains evidence, not authority.
- The project refuses to encode an unsupported commercial-license claim.
- Model replacement does not change the Judge contract.
- Golden evaluation must report the selected model revision and inference configuration.

## Traceability

F1 tests must cover PT → EN support; PT → EN contradiction; PT/PT support and contradiction; EN/EN support and contradiction; deterministic numeric/date/unit/negation precedence over NLI; NLI `NEUTRAL` preservation; provenance hashes; rejected/unapproved model configuration; and Judge-only verdict authority.
