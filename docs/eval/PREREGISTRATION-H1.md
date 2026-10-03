# Pre-registration — H1 Sentence Aggregation

Status: frozen before any H1 evaluation run.
Date: 2026-10-03
Base: E1 (`aa11090800d9737a26875f78e4158405e7c6afd3`), with Golden v0 and v0.1 frozen and unchanged.

## 1. Hypothesis

H1 tests whether sentence-level evidence aggregation improves stance classification over the current 512-character evidence-window baseline.

Primary path: B — translation + NLI.
Secondary path: A — direct multilingual NLI.
Path C is not modified by H1 and remains the deterministic reference.

## 2. Fixed method

1. The evidence excerpt is segmented into sentences using deterministic punctuation boundaries.
2. Each claim is evaluated independently against every resulting evidence sentence.
3. NLI is run on claim × sentence pairs using the exact model, model revision, translation model/revision, thresholds, and tie precedence already frozen for E1.
4. The selected stance is the candidate with maximum confidence across sentences.
5. If confidence is tied, `contradicts` wins over `supports`, which wins over `neutral`, matching the existing E1 precedence.
6. No threshold, model, model revision, translation model, Judge rule, provenance rule, or final-verdict rule is changed.
7. Sentence offsets are retained in provenance and the input hash covers the claim plus the selected evidence sentence.
8. If an excerpt contains no detected sentence boundary, the complete excerpt is one sentence.

## 3. Comparison

H1 is compared against the E1 512-character window baseline on the same Golden v0 and Golden v0.1 case ids.

The primary analysis is B-H1 versus B-E1.
The secondary analysis is A-H1 versus A-E1.

Path C is unchanged and is reported only as the deterministic reference.

## 4. Metrics

Primary metric: balanced accuracy.

Secondary metrics:
- accuracy
- macro-F1
- 95% bootstrap CI with 10,000 iterations, seed 20261003
- ECE
- latency p50/p95
- abstention
- precision and coverage for VERIFIED and SUPPORTED
- accuracy by category and expected state
- exact paired McNemar on the same case ids, H1 versus the E1 baseline

The same metric definitions used by E1 are retained.

## 5. Disclosure and development-set boundary

The author had access to E1 results before freezing this hypothesis. H1 is therefore a development experiment, not an unbiased confirmatory test.

Golden v0 and v0.1 remain development sets. No generalization claim is made from H1. Generalization requires the hidden Golden v1.

## 6. Decision rule

H1 is considered useful only if its measured results and paired comparison provide evidence of improvement without changing the frozen model/rule configuration.

No threshold for acceptance is introduced after seeing results.

## 7. Reproducibility

Seed: 20261003.
Bootstrap iterations: 10,000.

The H1 report must include the exact evaluation commit, Golden SHA-256 values, model/revision identifiers, report SHA-256 values, and links to the GitHub Actions jobs.
