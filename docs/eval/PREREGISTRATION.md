# F1.1 Preregistration

**Status:** frozen before Golden v0 re-measurement  
**Date:** 2026-10-03  
**Development-set warning:** Golden v0 is a development/evaluation-development corpus for this phase. It must not be used to tune thresholds or choose rules after observing its results.

## Part 5 — Statistical analysis and power

Primary endpoint: accuracy over the 30 scored Golden v0 cases. The 4 ABSTAIN contracts are reported separately.

Frozen majority baseline: 13/30 = 43.33%.

For a one-sided exact binomial test at alpha = 0.05 against p0 = 13/30, 18/30 (60.0%) is the first integer accuracy level whose tail probability is below 0.05 (approximately 0.0493). This is a small-sample detectability threshold, not a claimed effect-size target.

Illustrative prospective power calculation for a true accuracy of 60% with n=30 gives approximately 57.85% power for the corresponding one-sided binomial rejection rule. Thus n=30 is underpowered for reliably detecting a modest improvement over the majority baseline.

The paired McNemar analysis remains the primary comparison against the frozen F0/legacy system. Bootstrap confidence intervals use 10,000 resamples with the frozen seed 20261003.

No threshold, rule, model or case selection may be changed after inspecting Golden v0 results.

## Part 6 — External measurement plan

External evaluation is kept separate from Golden v0 and is never used to tune F1.1.

1. **Datasets:** PsiloQA, MultiHal and any additional multilingual factuality benchmark with a documented license.
2. **Language slices:** report PT, EN and aggregate separately; do not infer PT performance from translated EN-only results.
3. **Models:** evaluate A, B, C and optional external comparators such as Granite Guardian and MiniCheck under their license gates.
4. **Metrics:** accuracy, balanced accuracy, per-class confusion matrix, macro-F1 where labels permit, ECE, bootstrap 95% CI, p50/p95 latency, and paired tests where the same cases are evaluated.
5. **Audit:** record dataset revision, model revision, license, retrieval corpus hash, configuration hash, software commit and report SHA-256.
6. **No contamination:** external benchmark labels and cases must never be copied into Golden v0.
7. **Reproducibility:** all measurements must run from a fixed revision and produce machine-readable artifacts plus a human-readable report.

## Part 7 — Code quality and reproducibility

`ruff check .`, strict `mypy` and the complete `pytest` suite are mandatory gates before Golden measurement.

Broad lint suppressions such as `# ruff: noqa` are prohibited. The P0c reproducer must pass Ruff without suppressing the file.
