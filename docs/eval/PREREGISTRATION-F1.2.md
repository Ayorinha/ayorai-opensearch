# Pre-registration — F1.2: rule path C after the Portuguese stance fixes

Status: frozen before any F1.2 measurement. Changes only by dated amendment at the end of this file.
Date: 2026-10-09
Author: Claude (Anthropic), at the request of the project owner.

## 1. What changed since F1

| PR | Change | Affects |
|---|---|---|
| #110 | fail-closed licence level and guard on translation/NLI backends | provenance strings only; no stance logic |
| #111 | `RuleStanceDetector` v4 → v5: language-dependent negation; Portuguese written, slash and month dates; directional antonyms | path C only |

Code-path analysis: `NLIStanceDetector` and `TranslatedNLIStanceDetector` (paths A and B) do not call any helper changed by #111 (`_has_negation`, `_direction_conflict`, `_extract_dates`, `_dates_conflict`, `_strip_dates`, `_fact_tokens`, `_numeric_facts_align`). Paths A and B are therefore **not re-measured** in F1.2. Their F1 numbers stand unchanged. A reproducibility re-run of A/B under locked dependencies is separate future work.

## 2. Hypothesis

H1.2: on Golden v0 and on Golden v0.1, path C with `RuleStanceDetector` v5 has balanced accuracy greater than or equal to v4, with no case that v4 gets right and v5 gets wrong in the categories `conflict-negation` and `conflict-date`.

## 3. Design

- **Baseline:** `RuleStanceDetector` v4 at commit `d245e681bad2e5c149a252a2ecfa0f7fe65af3f8` (main after #110, before #111).
- **Candidate:** `RuleStanceDetector` v5 at the main commit that contains this pre-registration (after #111).
- **Data:** Golden v0 (`2613aefccf232989833b80c0d23257e6e9f312e0f6b720801a0658407b2f1c75`), Golden v0.1 (`a7076512196c1ee9670478f036f7a3996fe89a483efad140ec7b985a54846fb9`), corpus (`ce2333ccfe4003ebfc90819400beaf6a245620754deb8572c7611bd8bbb7dea3`). All unchanged.
- **Runner:** `scripts/run_f1_2_eval.py`, committed with this pre-registration. It reuses `_evaluate` from `scripts/run_f1_eval.py` (same pipeline, scope classifier, fixture retriever and metrics as F1). Baseline runs the same script with the baseline package on `PYTHONPATH`; the report records detector version and source commit.
- Both runs are deterministic (no model, no randomness except the seeded bootstrap).

## 4. Metrics

- **Primary:** balanced accuracy, per suite.
- **Secondary:** accuracy, macro-F1, accuracy 95% CI by bootstrap (10,000 iterations, seed 20261003), majority-class baseline, accuracy by category and by expected state.
- **Paired test:** exact McNemar on per-case correctness, baseline vs candidate, per suite (n = 30 cases with a global verdict).
- **Change log:** every case whose prediction changes is listed with expected, baseline and candidate verdicts.

## 5. Decision rules (fixed now)

- The candidate is reported as **improved** on a suite only if balanced accuracy increases **and** exact McNemar p < 0.05.
- If balanced accuracy increases with p ≥ 0.05, it is reported as **directional improvement, not statistically significant** (n = 30 is underpowered).
- If balanced accuracy decreases, or H1.2's category condition fails, it is reported as a **regression**, with the affected cases listed.
- **Consistency check:** the baseline v4 accuracy is compared with the published F1/E1 path C numbers (v0 26.67%, v0.1 33.33%). Any mismatch is reported as is and explained from the commit history; nothing is re-run to make them match.

## 6. Integrity rules

- One measurement run of baseline and candidate, then publication in `docs/eval/F1.2-RESULTS.md` with commit SHAs and report SHA-256s, whatever the result.
- No rule, threshold or code change is made in response to the F1.2 result within F1.2. Any later rule change requires a new pre-registration, and claims of generalization remain reserved for the hidden Golden v1.
- Golden v0/v0.1 remain development sets. F1.2 is not evidence of Portuguese-document generalization (the corpus is 52 synthetic `en-US` documents).

## 7. Disclosures

- The #111 fixes were derived from code review and new adversarial tests that do not copy Golden text. However, the author had read `docs/eval/F1-RESULTS.md` (per-case error table with categories such as `conflict-negation` and `conflict-date`) and `docs/eval/PREREGISTRATION-GOLDEN-v0.1.md` (which lists v0.1 claim texts). One v0.1 claim text (case x02, "... no fim de 2025") was used in a local manual check to confirm the negation defect before the fix was written. This is a contamination risk for v0.1 and is the reason F1.2 cannot support any generalization claim.
- The repository's CI job `golden-regression` recomputes the Golden v0 runner automatically on every push, including the #111 PR. Its numeric output was not read by the author and was not used for any decision.
- F1 path A/B and E1 numbers were produced by multiple workflow runs on 2026-10-03/04; F1.2 does not revisit them.

## 8. Execution

1. Merge this pre-registration (with the runner) to main with CI green.
2. `python scripts/run_f1_2_eval.py measure --out reports/f1.2-candidate.json` on that main commit.
3. In a worktree at the baseline commit: `PYTHONPATH=<worktree>/src python scripts/run_f1_2_eval.py measure --out reports/f1.2-baseline.json` (runner from step 1).
4. `python scripts/run_f1_2_eval.py compare --baseline reports/f1.2-baseline.json --candidate reports/f1.2-candidate.json --preregistration-commit <sha> --out-json reports/f1.2-results.json --out-md docs/eval/F1.2-RESULTS.md`.
5. Publish via PR, verbatim, with the interpretation required by §5.
