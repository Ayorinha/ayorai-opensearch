# F1 Results — Golden v0

Evaluation commit: c4b73f4af75ddad4d74dc8887897e0d394249422
CI: https://github.com/Ayorinha/ayorai-opensearch/actions/runs/37146515354
Golden SHA-256: 2613aefccf232989833b80c0d23257e6e9f312e0f6b720801a0658407b2f1c75
Corpus SHA-256: ce2333ccfe4003ebfc90819400beaf6a245620754deb8572c7611bd8bbb7dea3
Threshold/config SHA-256: d64d233a3c31f83d09cfb59504ca8c580008fa8262dbe1d52dd6550afc6020cb
Seed: 20261003
Bootstrap: 10,000

## Paths

| Path | Status |
|---|---|
| A — multilingual direct NLI | measured, EVAL_ONLY |
| B — translate-then-verify | measured, EVAL_ONLY, non-commercial |
| C — rules-only | measured ablation |

## Metrics

| System | Accuracy | Balanced | IC95% | ECE | p50 ms | p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| A | 0.4000 | 0.3526 | [0.2333, 0.5667] | 0.5353 | 371.399 | 743.996 |
| B | 0.4333 | 0.5272 | [0.2667, 0.6000] | 0.5049 | 1835.382 | 4209.567 |
| C | 0.2667 | 0.4402 | [0.1333, 0.4333] | 0.4093 | 0.123 | 0.591 |
| Majority baseline | 0.4333 | — | — | — | — | — |

## McNemar

A vs F0/C: {'left_correct_right_wrong': 2, 'right_correct_left_wrong': 6, 'exact_p': 0.2890625}
B vs F0/C: {'left_correct_right_wrong': 1, 'right_correct_left_wrong': 6, 'exact_p': 0.125}
A vs legacy: {'legacy_correct_new_wrong': 5, 'new_correct_legacy_wrong': 4, 'exact_p': 1.0}

## A error analysis

| Case | Category | Expected | Predicted | Cause | Max resolvable |
|---|---|---|---|---|---:|
| c01 | comparison | CONFLICTING | PARTIALLY_SUPPORTED | stance/NLI; comparison | 1 |
| c02 | comparison | PARTIALLY_SUPPORTED | CONFLICTING | stance/NLI; comparison | 1 |
| c03 | mock-only | UNVERIFIED | REFUTED | stance/NLI | 1 |
| x01 | conflict | CONFLICTING | UNVERIFIED | stance/NLI; conflict semantics | 1 |
| x02 | conflict | CONFLICTING | UNVERIFIED | stance/NLI; conflict semantics | 1 |
| x03 | conflict | CONFLICTING | PARTIALLY_SUPPORTED | stance/NLI; conflict semantics | 1 |
| r01 | independence-republication | PARTIALLY_SUPPORTED | UNVERIFIED | metadata/independence | 1 |
| r02 | independence-republication | PARTIALLY_SUPPORTED | REFUTED | metadata/independence | 1 |
| h01 | independence-hash | PARTIALLY_SUPPORTED | REFUTED | metadata/provenance | 1 |
| ch01 | independence-citation-chain | PARTIALLY_SUPPORTED | REFUTED | metadata/provenance | 1 |
| p01 | provenance-complete | VERIFIED | UNVERIFIED | Judge/aggregation | 1 |
| p02 | provenance-incomplete | SUPPORTED | UNVERIFIED | metadata/provenance | 1 |
| x04 | conflict-date | CONFLICTING | UNVERIFIED | stance/NLI; date contradiction | 1 |
| x05 | conflict-negation | CONFLICTING | VERIFIED | stance/NLI; negation | 1 |
| x06 | conflict-entity | CONFLICTING | REFUTED | stance/NLI; entity alignment | 1 |
| nt01 | numeric-tolerance | VERIFIED | UNVERIFIED | metadata/numeric | 1 |
| nt02 | numeric-tolerance-boundary | VERIFIED | UNVERIFIED | metadata/numeric | 1 |
| nt03 | numeric-tolerance-boundary | CONFLICTING | UNVERIFIED | metadata/numeric | 1 |

Upper-bound errors by cause: {'a': 9, 'b': 1, 'c': 8}

## Statistical limitation

With n=30, exceeding the 43.33% majority baseline with p<0.05 requires approximately 60% accuracy in this small paired setting. A's 95% bootstrap interval includes the baseline.

No threshold was tuned against Golden v0. ADR-002 remains the sole final-verdict authority.

Report SHA-256: 0c7fad3b4bc4db96f888ac0b26f45bb4b0f7616a6e63e8df5bfb7d73a30342a9


## E1 Audit Disclosures

- **A** is EVAL_ONLY because its model license is not cleared for commercial use; **B is the candidate commercial path** subject to independent license verification.
- **Golden v0 and v0.1 are development sets.** The v0.1 rewrite was authored after the author had seen per-case Path C results, as disclosed in the pre-registration. Generalization is reserved for the hidden Golden v1.
- **Path C nearly did not improve on v0.1:** the deterministic reference reproduced locally at 10/30 (balanced accuracy 0.481838; 95% bootstrap CI [0.1667, 0.5000]).

## E2 Audit Conclusion

Claude audit approved commit `22579cfbec65351d7a95b795ad8bf9e10786de27`.

- H1 is **inconclusive for long documents**: 35/40 Golden documents have one sentence and none exceeds 512 characters, so H1 is equivalent to the existing 512-character window on those cases.
- On the 5 two-sentence documents, H1 was harmful for path B (**-3 cases**).
- H1 is **not promoted**. It will be retested on the hidden Golden v1 or in F3 with genuinely long multi-sentence documents. H1 must not be rerun on this Golden.
- The prior translation diagnosis was incorrect: the document is translated in full before sentence splitting, and the 5 affected documents are en-US and therefore not translated.
- **Limitação:** em documentos traduzidos, a proveniência aponta para a evidência original inteira, não para a frase exata. Alinhamento frase a frase fica para a F2.


## E3 Audit Reconciliation

Claude audit approved E3 measurement at commit `7309a24107d736395c2b64f48fc737370e28ceb8`.

- **Gold-label deviation:** E3 used the case-level **GLOBAL** verdict as the binary gold, not the claim-level stance specified by the E3 amendment. The implemented binary mapping is `SUPPORTS/SUPPORTED/VERIFIED -> SUSTENTADO`; all other global verdicts, including `PARTIALLY_SUPPORTED` and `CONFLICTING`, map to `NAO_SUSTENTADO`. The E3 measurement remains valid as a measurement of this explicitly documented case-level binary task; it is **not** a claim-level rerun and will not be rerun on this Golden.
- **Binary majority baseline:** 23/30 = **76.67%**. Any binary A/B/C accuracy cited for the E3 comparison must be read against this baseline.
- **E3 amendment provenance:** commit `e566c856af415ef2bd55b342560434ff5dcdc471` was **not isolated**; it included the preregistration amendment plus the E3 script/CI work. The E3 measurement occurred later, and this provenance correction does not invalidate the measurement.
- The E3 evaluator now computes binary A/B/C **accuracy, balanced accuracy, and bootstrap IC95% (10,000; seed 20261003)** from the same case-level binary rule. No rule, threshold, or historical E3 measurement was changed by this code move.
- E3 JSON confirmation: **D1 unsupported_case_count = 18 (v0), 8 (v0.1); D2 = 14 (v0), 1 (v0.1)**.
- **Interpretation:** LettuceDetect is a detector of unsupported/invented content, not a source-conflict resolver. Of the 23 negative cases under the global binary gold, **21 are PARTIALLY_SUPPORTED or CONFLICTING**, so most negatives are outside the detector's intended semantic target.
- The preregistered D1 expectation was wrong in the opposite direction: the English-only detector was expected to tend toward `NAO_SUSTENTADO` for Portuguese claims, but the observed D1 behavior did not produce that expected failure mode. This is recorded as an outcome, not used to adjust the method.


## E4 License-policy correction — 2026-10-08

The status row above describing Path B as EVAL_ONLY, non-commercial is corrected by the normative registry at docs/legal/MODEL-LICENSE-POLICY.md, verified 2026-10-03. Under its uniform eligibility rule, the registered Path B translation model and NLI model are COMMERCIAL_DEFAULT; the registry retains an explicit legal-risk note for the translation model because the OPUS source-license inventory is incomplete. This classification is a policy classification, not legal advice or a guarantee of unrestricted commercial use.

The implementation defect was that MarianTranslationBackend.provenance_version hard-coded license=EVAL_ONLY, contradicting the registry. The backend now accepts an explicit license_level parameter and defaults to COMMERCIAL_DEFAULT, matching the current Path B registry; restricted uses can explicitly pass EVAL_ONLY. Regression tests assert both provenance values and reject unknown levels.

**Measurement integrity:** this is a dated policy/provenance correction only. No Golden, corpus, threshold, metric, historical evaluation, or result has been rewritten or rerun. The F1 numbers above remain exactly as measured; interpret the former Path B status label as superseded by this correction.
