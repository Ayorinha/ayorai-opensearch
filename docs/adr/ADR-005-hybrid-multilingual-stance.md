# ADR-005 — Hybrid Multilingual Stance Detection

Status: Accepted for F1
Date: 2026-10-03
Scope: F1 multilingual stance evidence

## Decision

The stance layer is hybrid. Deterministic rules for numbers, dates, units and negation have priority when they fire. A three-class NLI backend handles the remaining claim/evidence pairs. Neither path may select the final verification verdict.

## Context

F0 exposed a cross-lingual failure mode: Golden claims are predominantly Portuguese while relevant corpus evidence is English. The existing lexical rule detector depends on token overlap and therefore produces excessive NEUTRAL edges for valid cross-language entailment.

ATTRACTOR needs stance evidence for PT to EN, PT to PT, EN to EN and EN to PT where the selected backend supports it.

## Hybrid precedence

For each claim/evidence pair:

1. Parse deterministic numeric facts.
2. Compare dates at the granularity actually expressed.
3. Compare units and unit-bearing quantities.
4. Detect explicit negation in the supported PT/EN lexicon.
5. If a deterministic contradiction is established, emit CONTRADICTS.
6. If a deterministic equality/support condition is established, emit SUPPORTS.
7. Otherwise, delegate to the configured three-class NLI backend.
8. Preserve the backend SUPPORTS, CONTRADICTS or NEUTRAL output as a stance edge with provenance.

A deterministic rule firing outranks model inference for the rule domain. NLI cannot override a triggered hard rule.

## Judge boundary

The NLI backend and deterministic rules produce only stance edges and component provenance. They do not select a final verdict, aggregate clusters, decide provenance completeness, or change the caller-supplied claim. ADR-002 remains the sole authority for the final verdict.

## Provenance

Every emitted stance edge records component name, model/backend identifier, backend version, input SHA-256 over the claim/evidence pair, and output SHA-256 over the result. For EVAL_ONLY backends, evaluation mode or explicit license opt-in is encoded in the provenance version.

## Model license policy

The normative policy is docs/legal/MODEL-LICENSE-POLICY.md.

A, the multilingual direct NLI model, is EVAL_ONLY. Its weights are MIT, but its declared training data includes XNLI, so it is not a commercial default.

B, translate-then-verify, is currently BLOCKED. The English NLI checkpoint has Apache-2.0 weights and declared SNLI/MultiNLI training data. The proposed PT to EN OPUS translation checkpoint does not expose a complete immutable per-source training-data license inventory. Under the policy that is insufficient for COMMERCIAL_DEFAULT.

## NLI dependency boundary

The optional nli extra provides transformers and CPU torch. Importing the base package does not require either dependency.

The backend interface is narrow: classify(claim_text, evidence_text) returns stance and confidence. The implementation validates id2label explicitly. No positional assumption about 0, 1 and 2 is permitted without reading and validating id2label.

## Evaluation controls

F1 evaluation freezes configs/f1-thresholds.json before measurement. NLI uses argmax and has no tunable case-specific threshold. Bootstrap uses 10,000 iterations with seed 20261003.

Golden v0 is evaluated in closed-world mode. Results include accuracy, balanced accuracy, bootstrap IC95%, McNemar versus legacy and F0/C, six-by-six confusion matrix, accuracy by state and category, ECE, and p50/p95 latency.

No evaluation result is used to alter ADR-002.

## Consequences

- Cross-language stance is tested directly with the EVAL_ONLY multilingual NLI model.
- Numeric/date/unit/negation safety rules remain deterministic and auditable.
- License uncertainty is explicit rather than hidden.
- No model weights are redistributed by ATTRACTOR.
- B can be reopened when complete translation training-data license evidence is available.
- Golden v0 remains frozen; thresholds cannot be tuned after seeing its outcomes.

This policy is not legal advice; review by an intellectual-property specialist is recommended before commercial use.
