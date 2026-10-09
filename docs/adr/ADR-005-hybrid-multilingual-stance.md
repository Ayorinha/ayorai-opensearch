# ADR-005 — Hybrid Multilingual Stance Detection

Status: Accepted for F1
Date: 2026-10-03

## Decision

The stance layer is hybrid. Deterministic rules for numbers, dates, units and negation have priority when they fire. A three-class NLI backend handles the remaining claim/evidence pairs. Neither path may select the final verification verdict.

## Cross-language paths

F1 measures three frozen paths:

- A: direct multilingual NLI, EVAL_ONLY.
- B: translate-then-verify, EVAL_ONLY and deliberately non-commercial. When languages differ, the Portuguese side is translated to English before NLI.
- C: rules-only ablation.

The evidence shown to the audit trail remains the original source excerpt; translated text is used only as model input.

## Hybrid precedence

For each claim/evidence pair:

1. Parse deterministic numeric facts.
2. Compare dates at the granularity actually expressed.
3. Compare units and unit-bearing quantities.
4. Detect explicit negation in the supported PT/EN lexicon.
5. If a deterministic contradiction is established, emit CONTRADICTS.
6. If a deterministic equality/support condition is established, emit SUPPORTS.
7. Otherwise, delegate to the configured three-class NLI backend.

A deterministic rule firing outranks model inference for the rule domain. NLI cannot override a triggered hard rule.

## Evidence windows and aggregation

configs/f1-thresholds.json is versioned and read by the F1 evaluation. Evidence is divided into 512-character windows with 64-character overlap. The detector aggregates window predictions by maximum confidence, with explicit tie precedence. The winning absolute source offsets are recorded in stance provenance. This preserves one stance edge per evidence item.

The NLI decision is argmax; no confidence threshold is tuned against Golden v0.

## Judge boundary

NLI, translation and deterministic rules produce only stance edges and component provenance. They do not select a final verdict. ADR-002 remains the sole authority for the final verdict.

## Provenance

Every emitted stance edge records component, model/backend, version, input SHA-256 and output SHA-256. B additionally records the translation provenance hash and winning window offsets.

## Model license policy

The normative policy is docs/legal/MODEL-LICENSE-POLICY.md. A is EVAL_ONLY because its declared training includes XNLI. B is COMMERCIAL_DEFAULT under the policy's uniform declared-data rule; the OPUS source-license inventory remains incomplete and is recorded as a legal risk, not silently reclassified as NC. This policy classification is not legal advice or a guarantee of unrestricted commercial use.

## Evaluation controls

Golden v0 is frozen. Metrics use seed 20261003 and 10,000 bootstrap iterations. The report includes accuracy, balanced accuracy, IC95%, McNemar, confusion matrices, category/state breakdown, ECE and p50/p95 latency. The report also classifies every A error into stance/NLI, Judge/aggregation or metadata categories and gives an upper-bound number of errors that each correction could resolve.

With n=30, a paired improvement over the 43.33% majority baseline at p<0.05 requires approximately 60% accuracy. A's 95% bootstrap interval includes the baseline.

No release or tag is created by F1. ADR-002 remains the final-verdict authority.

This policy is not legal advice; review by an intellectual-property specialist is recommended before commercial use.
