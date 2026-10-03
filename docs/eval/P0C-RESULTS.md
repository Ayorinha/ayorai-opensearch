# P0.c — Claim-level pipeline pre-fix result

## Scope

This artifact records the measured DEV result immediately before F0 stabilization. It is not a post-fix benchmark and does not represent a release-quality accuracy claim.

- Branch: `p0-pipeline`
- Pre-fix commit: `b4cdc78dff0bda4284590e5f71a3d647e06db2f2`
- CI merge ref: `598e17d8bf4bfed4af1d66fa8e86e9cbcf5bebe6`
- CI run: `37128251283`
- Golden v0 labeled cases: 30
- Golden v0 total cases: 34
- Corpus documents: 52

## Measured DEV result

| Metric | Result |
|---|---:|
| Accuracy | 8/30 = 26.7% |
| Balanced accuracy | 44.0% |
| 95% CI | [13.3%, 43.3%] |
| McNemar vs legacy | 9 vs 4 |
| McNemar p-value | 0.27 |
| Abstraction cases correct | 0/4 |
| CONFLICTING | 0/8 |
| Independence cases | 0/4 |
| Multi-hop | 0/3 |

## Root cause observed

The fixture corpus is English while the current rule stance path receives Portuguese claims. The lexical detector therefore produces mostly NEUTRAL/unsupported behavior, and the source-independence clustering path is not meaningfully exercised.

A separate deterministic bug was identified in the F0 CI failures: numeric comparison performed a cross-product over all numbers in two evidence texts, allowing unrelated values such as a year and an amount to trigger contradiction.

## Reproduction contract

The post-fix result is intentionally not recorded here. After the F0 branch is green, publish the new commit SHA, dataset/manifest version, seed where applicable, confidence interval, baseline, and exact command used for reproduction in a new result artifact.

The frozen suite remains DEV data and must not be tuned case-by-case.
