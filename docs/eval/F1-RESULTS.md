# F1 Results — Golden v0

Evaluation commit: 92b9fcc5675744f89bc9a7991cd39c78f1897dfa
CI run: https://github.com/Ayorinha/ayorai-opensearch/actions/runs/37142483048
Golden SHA-256: 2613aefccf232989833b80c0d23257e6e9f312e0f6b720801a0658407b2f1c75
Corpus SHA-256: ce2333ccfe4003ebfc90819400beaf6a245620754deb8572c7611bd8bbb7dea3
Threshold/config SHA-256: d64d233a3c31f83d09cfb59504ca8c580008fa8262dbe1d52dd6550afc6020cb
Seed: 20261003
Bootstrap: 10,000

## Paths

| Path | Status |
|---|---|
| A — multilingual direct NLI | measured, EVAL_ONLY |
| B — translate-then-verify | blocked: no complete per-source OPUS training-data license inventory for the selected PT to EN checkpoint |
| C — rules-only | measured ablation |

## Metrics

| System | Accuracy | Balanced | IC95% | ECE | p50 ms | p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| A | 0.4000 | 0.3526 | [0.2333, 0.5667] | 0.5353 | 370.462 | 754.709 |
| C | 0.2667 | 0.4402 | [0.1333, 0.4333] | 0.4093 | 0.115 | 0.560 |
| Majority baseline | 0.4333 | — | — | — | — | — |

## McNemar

A vs F0/C: f0_correct_nli_wrong=2, nli_correct_f0_wrong=6, exact_p=0.2890625

A vs legacy: legacy_correct_new_wrong=5, new_correct_legacy_wrong=4, exact_p=1.0

## Confusion matrix — A

{
  "VERIFIED": {"VERIFIED": 3, "SUPPORTED": 0, "PARTIALLY_SUPPORTED": 0, "UNVERIFIED": 3, "REFUTED": 0, "CONFLICTING": 0},
  "SUPPORTED": {"VERIFIED": 0, "SUPPORTED": 0, "PARTIALLY_SUPPORTED": 0, "UNVERIFIED": 1, "REFUTED": 0, "CONFLICTING": 0},
  "PARTIALLY_SUPPORTED": {"VERIFIED": 0, "SUPPORTED": 0, "PARTIALLY_SUPPORTED": 8, "UNVERIFIED": 1, "REFUTED": 3, "CONFLICTING": 1},
  "UNVERIFIED": {"VERIFIED": 0, "SUPPORTED": 0, "PARTIALLY_SUPPORTED": 0, "UNVERIFIED": 0, "REFUTED": 1, "CONFLICTING": 0},
  "REFUTED": {"VERIFIED": 0, "SUPPORTED": 0, "PARTIALLY_SUPPORTED": 0, "UNVERIFIED": 0, "REFUTED": 1, "CONFLICTING": 0},
  "CONFLICTING": {"VERIFIED": 1, "SUPPORTED": 0, "PARTIALLY_SUPPORTED": 2, "UNVERIFIED": 4, "REFUTED": 1, "CONFLICTING": 0}
}

## Accuracy by category — A

| Category | Accuracy | n |
|---|---:|---:|
| comparison | 0.0000 | 2 |
| conflict | 0.0000 | 3 |
| conflict-date | 0.0000 | 1 |
| conflict-entity | 0.0000 | 1 |
| conflict-negation | 0.0000 | 1 |
| factual | 1.0000 | 4 |
| independence-citation-chain | 0.0000 | 1 |
| independence-hash | 0.0000 | 1 |
| independence-republication | 0.0000 | 2 |
| injection | 1.0000 | 3 |
| injection-factual-corroborated | 1.0000 | 1 |
| mock-only | 0.0000 | 1 |
| multi-hop | 1.0000 | 3 |
| numeric-tolerance | 0.0000 | 1 |
| numeric-tolerance-boundary | 0.0000 | 2 |
| provenance-complete | 0.0000 | 1 |
| provenance-incomplete | 0.0000 | 1 |
| refuted | 1.0000 | 1 |

## Accuracy by state — A

| State | Accuracy | n |
|---|---:|---:|
| CONFLICTING | 0.0000 | 8 |
| PARTIALLY_SUPPORTED | 0.6154 | 13 |
| REFUTED | 1.0000 | 1 |
| SUPPORTED | 0.0000 | 1 |
| UNVERIFIED | 0.0000 | 1 |
| VERIFIED | 0.5000 | 6 |

## Interpretation

No path exceeded the 43.33% majority-class baseline. A reached 40.00% accuracy, with a bootstrap 95% interval of 23.33%–56.67%; C remained at 26.67%. Therefore F1 does not satisfy the exit criterion on this frozen Golden v0.

A improved over C by 6 correct cases versus 2 regressions in the paired comparison, but the exact McNemar p-value is 0.2890625. Against the legacy implementation, A has 4 wins versus 5 losses, exact p=1.0.

The most important residual failure is CONFLICTING: A scored 0/8 in that state. Multi-hop scored 3/3, while several deterministic numeric/tolerance and conflict categories remained at 0 accuracy. No threshold was tuned after seeing Golden v0.

ADR-002 remains the sole final-verdict authority; A supplies stance evidence only.

Report SHA-256 (JSON artifact): f302fb03368bfebb7308d3f23ef9f97dcf2c70a5aa1901fb7d24b3dcea1b5883
