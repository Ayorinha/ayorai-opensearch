# Judge 2.0.0 — G1/G2 and E1–E3 pre-adjudication report

**Status:** implementation candidate; not independently approved and not yet verified by CI at the time this report was drafted.  

> **State note (2026-10-13):** the gates described here were merged to `main` with required CI checks passing and were published in v0.5.0. The original status line above is preserved as a historical record of when this report was drafted.

**Scope:** Onda 2, item 2.2.  
**Normative contract:** ADR-009 and `rules/judge-2.0.0.json`.  
**Contract `rules_sha256`:** `493cce66ce45fcb432b8345e7567cfb39858492bfe46d5fa6b584991e79e9efc`.  
**Base commit:** `07e95680a24b5ffcbba903314929c261cdcc4c88` (SQUASH merge of PR #150).

## What this isolated item implements

- G1 validates the protocol version, claim text, atom collection and spans, unique IDs, stance references, and duplicate atom/evidence stance pairs.
- G1 failures reuse `InvalidJudgeInput` and return `decision_state=INVALID_INPUT` with the matching `reason_codes`.
- G2 records applicable abstention reasons and returns `decision_state=ABSTAINED`; G2 takes precedence over evidence admission.
- E1 distinguishes unavailable source text (`SOURCE_UNAVAILABLE`) from invalid offsets (`OFFSET_INVALID`).
- E2 always requires `NFC(source_text[start_offset:end_offset]) == NFC(excerpt)`; a supplied normalized-content SHA-256 is an additional whole-source integrity check, never a substitute for excerpt equality.
- Offsets are Python Unicode code-point offsets into the original source text; excerpt comparison normalizes NFC only after slicing.
- E3 requires an explicit `SUPPORTS` or `CONTRADICTS` relation between the evidence item and atom.
- Each evidence/atom pair is recorded as admitted or excluded with its reason.

## Deliberate boundaries

- This item does **not** calculate atomic or composite factual verdicts.
- The result type intentionally has no `verdict` field.
- The item does not replace `r1-a`, change the public API route, migrate Goldens, or modify frozen evaluation artifacts.
- The implementation has no network client or network call.
- G1/G2 validation and E1–E3 admission are a pre-adjudication foundation only; full T1–T10 coverage and later adjudication remain separate work.

## Test mapping

`tests/verification/test_judge2_gates.py` includes a dedicated negative case for each of the eight G1 codes, cases for each G2 reason, and a case for each E1/E2/E3 rejection reason. It also pins the contract digest and checks that results expose no verdict field.

**Verification rule:** do not mark this implementation verified until CI is green and an independent reviewer has approved the exact final PR head SHA. The frozen Goldens, corpus, manifests, thresholds, and existing hashes must remain unchanged.
