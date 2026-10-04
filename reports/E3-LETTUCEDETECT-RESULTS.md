# E3 LettuceDetect Results — Audit Reconciliation

## Measurement status

Claude audit: **APPROVED as measurement** at commit `7309a24107d736395c2b64f48fc737370e28ceb8`.

This report records the audit reconciliation **without rerunning E3**.

## Gold and interpretation

The measured E3 gold was the **case-level GLOBAL verdict**, not claim-level stance as described in the amendment. The binary rule was:

- `SUPPORTS` / `SUPPORTED` / `VERIFIED` → `SUSTENTADO`
- every other GLOBAL verdict → `NAO_SUSTENTADO`, including `PARTIALLY_SUPPORTED` and `CONFLICTING`

The majority baseline for the 30 binary-eligible cases is **23/30 = 76.67% NAO_SUSTENTADO**.

The measurement is therefore valid only as this case-level binary experiment. **No claim-level rerun will be performed on this Golden.**

## D results

| Suite | Arm | Accuracy | Balanced | IC95% balanced | Unsupported cases |
|---|---|---:|---:|---:|---:|
| Golden v0 | D1 | 0.5000 | 0.4255 | [0.2308, 0.6481] | 18 |
| Golden v0 | D2 | 0.4333 | 0.4317 | [0.2115, 0.6635] | 14 |
| Golden v0.1 | D1 | 0.3667 | 0.4876 | [0.2708, 0.6731] | 8 |
| Golden v0.1 | D2 | 0.2667 | 0.5217 | [0.5000, 0.5714] | 1 |

Bootstrap: 10,000 iterations, seed 20261003.

## A/B/C binary comparison

The evaluator now computes binary A/B/C **accuracy, balanced accuracy and IC95%** directly from the same binary rule. The code change does not alter the E3 measurement.

The baseline must always be stated with any binary A/B/C accuracy: **23/30 = 76.67%**.

The previously observed binary accuracies were:
- Golden v0: A 0.8333, B 0.8333, C 0.8333.
- Golden v0.1: A 0.9000, B 0.8667, C 0.8333.

These are binary case-level comparisons, not claim-level stance accuracy.

## Audit findings

1. The E3 gold-label deviation is documented; no claim-level rerun.
2. `e566c85` was **not an isolated amendment-only commit**; it also contained script/CI work. The measurement happened afterward, so validity is preserved.
3. JSON confirms `unsupported_case_count`: D1 = 18/8 and D2 = 14/1 for v0/v0.1.
4. LettuceDetect detects unsupported/invented content; it does not resolve conflicts between sources. **21 of the 23 negative cases are PARTIALLY_SUPPORTED or CONFLICTING.**
5. The preregistered expectation that D1 would tend toward `NAO_SUSTENTADO` for Portuguese claims was wrong in the opposite direction. This is recorded as an observed outcome, not used to tune the method.

## Historical artifact hashes

- E3 JSON: `b6c6458e6463c97febc39769dff3b8651b1ddfa8ee15c4c4547977d43bf2bf6f`
- E3 Markdown: `3c1495da3d53f9e7edf13489a0d91df2bd48fd2a34e734040eb0e90b33f71150`
- F1 JSON captured with the E3 artifact: `17e080bbc2b0a41fa37a654f6d7090da3bf868352fb8f38eae47687528630e1b`
- E3 artifact ZIP: `610de685a08fa91ab7d8477e5487b9171bb68d2b25b2c87288932ce203cc04bf`
