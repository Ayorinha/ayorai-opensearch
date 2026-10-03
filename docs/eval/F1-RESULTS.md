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
