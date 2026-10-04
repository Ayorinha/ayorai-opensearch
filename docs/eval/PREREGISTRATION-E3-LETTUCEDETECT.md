# PREREGISTRATION — E3 LettuceDetect Evaluation

Status: frozen before E3 measurement
Date: 2026-10-04
Base commit: 86d1bdaf4464147416adcff7ac56259061629f7d

## Hypothesis and scope

E3 evaluates LettuceDetect as Path D, an evidence-span detector for unsupported claims.
It is **EVAL_ONLY**. It does not replace the deterministic Judge, FACT/NLI stance,
or final verdict. No training or fine-tuning is performed in E3.

Because Portuguese coverage is not established for LettuceDetect, evaluate:
1. PT direct: original Portuguese documents passed directly to the detector.
2. PT via translation: the full Portuguese document translated to English first,
   then evaluated by LettuceDetect.

The translation path is an evaluation-only comparison; translation is not a verdict rule.

## Frozen rules

- Do not change ADR-002 verdict precedence or thresholds.
- Do not tune thresholds against Golden v0 or v0.1.
- Do not rerun H1.
- Keep Golden v0 and v0.1 as development sets only.
- Generalization claims require hidden Golden v1.
- Record the exact LettuceDetect model/revision, weights/data license status,
  runtime, and translation model/revision.
- If weights or data licensing is not independently cleared for the intended use,
  retain the path as EVAL_ONLY.
- No LLM Judge is introduced.

## Evaluation

Use the same claim/evidence cases and fixed IDs from the current evaluation suites where
the detector's input assumptions permit measurement. Report coverage and supported-span
detection separately from final verdict accuracy; E3 is not a replacement for the
deterministic verdict pipeline.

Metrics:
- detector precision, recall, F1 where gold span labels exist;
- unsupported-span detection precision/recall/F1 where applicable;
- coverage/abstention;
- latency p50/p95;
- bootstrap 95% CI with 10,000 resamples, seed 20261003;
- per-category results;
- exact paired comparisons where a paired detector decision is defined.

For PT direct versus PT-translation, report paired results on the same eligible cases.
Do not infer general Portuguese performance beyond the measured Golden cases.

## Reproducibility

Report:
- commit SHA;
- Golden SHA-256;
- LettuceDetect model/revision;
- translation model/revision;
- licenses and source/date for external model/data claims;
- report SHA-256;
- GitHub Actions run/job/artifact links.

## Stopping rule

E3 ends after the two authorized evaluation paths (PT direct and PT via translation)
have been measured and reported, plus reproducibility metadata. No model training,
threshold optimization, or architecture promotion occurs in E3.

## Disclosure

E3 is authorized after the audited E2 result. The negative H1 result is known before
this preregistration and is not a criterion for selecting or tuning LettuceDetect.
